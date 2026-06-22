from __future__ import annotations

import copy
import re
import uuid
from typing import Any, Dict, Iterable, Iterator, Optional

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.errors import CollectionInvalid
import certifi

from app.core.config import MONGO_DATABASE, MONGO_URI

REQUIRED_COLLECTIONS = {
    "checkpoints_container": "checkpoints",
    "users_container": "USERS",
    "stores_container": "stores",
    "tags_container": "tags",
    "settings_container": "settings",
    "scan_container": "scan",
    "alerts_container": "alerts",
    "rounds_container": "rounds",
    "audit_logs_container": "audit_logs",
    "reports_container": "reports",
}


class InMemoryContainer:
    def __init__(self, container_id: str):
        self.id = container_id
        self._items: Dict[str, Dict[str, Any]] = {}

    def _clone(self, item: Dict[str, Any]) -> Dict[str, Any]:
        return copy.deepcopy(item)

    def _normalize_doc(self, body: Dict[str, Any]) -> Dict[str, Any]:
        doc = self._clone(body)
        doc_id = str(doc.get("id") or doc.get("_id") or uuid.uuid4())
        doc["id"] = doc_id
        doc["_id"] = doc_id
        return doc

    def create_item(self, body: Dict[str, Any]):
        item = self._normalize_doc(body)
        self._items[str(item["id"])] = item
        return self._clone(item)

    def read_item(self, item: str, partition_key: Any = None):
        record = self._items.get(str(item))
        if record is None:
            raise KeyError(item)
        return self._clone(record)

    def read_all_items(self):
        for record in self._items.values():
            yield self._clone(record)

    def replace_item(self, item: str, body: Dict[str, Any]):
        record = self._normalize_doc(body)
        record["id"] = str(item)
        record["_id"] = str(item)
        self._items[str(item)] = record
        return self._clone(record)

    def delete_item(self, item: str, partition_key: Any = None):
        if str(item) not in self._items:
            raise KeyError(item)
        del self._items[str(item)]

    def upsert_item(self, body: Dict[str, Any]):
        record = self._normalize_doc(body)
        self._items[str(record["id"])] = record
        return self._clone(record)

    def _parameter_map(self, parameters: Optional[Iterable[Dict[str, Any]]]) -> Dict[str, Any]:
        mapping: Dict[str, Any] = {}
        for param in parameters or []:
            name = str(param.get("name", ""))
            value = param.get("value")
            if name.startswith("@"):
                mapping[name] = value
                mapping[name.lstrip("@")] = value
        return mapping

    def _evaluate_clause(self, item: Dict[str, Any], clause: str, params: Dict[str, Any]) -> bool:
        clause = clause.strip()
        if not clause:
            return True

        param_match = re.match(r"(?i)c\.([A-Za-z0-9_]+)\s*=\s*@([A-Za-z0-9_]+)", clause)
        literal_match = re.match(r"(?i)c\.([A-Za-z0-9_]+)\s*=\s*'([^']*)'", clause)
        numeric_match = re.match(r"(?i)c\.([A-Za-z0-9_]+)\s*=\s*(\d+(?:\.\d+)?)", clause)

        if param_match:
            field, param_name = param_match.groups()
            expected = params.get(f"@{param_name}", params.get(param_name))
            return str(item.get(field)) == str(expected)

        if literal_match:
            field, expected = literal_match.groups()
            return str(item.get(field)) == expected

        if numeric_match:
            field, expected = numeric_match.groups()
            actual = item.get(field)
            try:
                return float(actual) == float(expected)
            except (TypeError, ValueError):
                return False

        return True

    def query_items(
        self,
        query: Optional[str] = None,
        parameters: Optional[Iterable[Dict[str, Any]]] = None,
        enable_cross_partition_query: bool = False,
    ):
        items = [self._clone(record) for record in self._items.values()]
        if not query:
            return items

        params = self._parameter_map(parameters)
        where_match = re.search(r"(?i)\bWHERE\b(.+)$", query)
        if not where_match:
            return items

        conditions = [
            part.strip()
            for part in re.split(r"(?i)\bAND\b", where_match.group(1))
            if part.strip()
        ]
        filtered = []
        for item in items:
            if all(self._evaluate_clause(item, clause, params) for clause in conditions):
                filtered.append(item)
        return filtered


class InMemoryDatabase:
    def __init__(self):
        self._containers: Dict[str, InMemoryContainer] = {}

    def create_container_if_not_exists(self, id: str):
        if id not in self._containers:
            self._containers[id] = InMemoryContainer(id)
        return self._containers[id]


class MongoCollectionAdapter:
    def __init__(self, collection: Collection):
        self.collection = collection

    def _clone(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        return copy.deepcopy(doc)

    def _normalize_doc(self, body: Dict[str, Any]) -> Dict[str, Any]:
        doc = self._clone(body)
        doc_id = str(doc.get("id") or doc.get("_id") or uuid.uuid4())
        doc["id"] = doc_id
        doc["_id"] = doc_id
        return doc

    def _parameter_map(self, parameters: Optional[Iterable[Dict[str, Any]]]) -> Dict[str, Any]:
        mapping: Dict[str, Any] = {}
        for param in parameters or []:
            name = str(param.get("name", ""))
            value = param.get("value")
            if name.startswith("@"):
                mapping[name] = value
                mapping[name.lstrip("@")] = value
        return mapping

    def _parse_filter(self, query: str, parameters: Optional[Iterable[Dict[str, Any]]]) -> Dict[str, Any]:
        params = self._parameter_map(parameters)
        where_match = re.search(r"(?i)\bWHERE\b(.+)$", query)
        if not where_match:
            return {}

        filters: Dict[str, Any] = {}
        conditions = [
            part.strip()
            for part in re.split(r"(?i)\bAND\b", where_match.group(1))
            if part.strip()
        ]

        for clause in conditions:
            param_match = re.match(r"(?i)c\.([A-Za-z0-9_]+)\s*=\s*@([A-Za-z0-9_]+)", clause)
            literal_match = re.match(r"(?i)c\.([A-Za-z0-9_]+)\s*=\s*'([^']*)'", clause)
            numeric_match = re.match(r"(?i)c\.([A-Za-z0-9_]+)\s*=\s*(\d+(?:\.\d+)?)", clause)

            if param_match:
                field, param_name = param_match.groups()
                filters[field] = params.get(f"@{param_name}", params.get(param_name))
            elif literal_match:
                field, expected = literal_match.groups()
                filters[field] = expected
            elif numeric_match:
                field, expected = numeric_match.groups()
                filters[field] = float(expected) if "." in expected else int(expected)

        return filters

    def create_item(self, body: Dict[str, Any]):
        item = self._normalize_doc(body)
        self.collection.insert_one(item)
        return self._clone(item)

    def read_item(self, item: str, partition_key: Any = None):
        doc = self.collection.find_one({"_id": str(item)})
        if doc is None:
            doc = self.collection.find_one({"id": str(item)})
        if doc is None:
            raise KeyError(item)
        return self._clone(doc)

    def read_all_items(self) -> Iterator[Dict[str, Any]]:
        for doc in self.collection.find():
            yield self._clone(doc)

    def replace_item(self, item: str, body: Dict[str, Any]):
        doc = self._normalize_doc(body)
        doc["id"] = str(item)
        doc["_id"] = str(item)
        self.collection.replace_one({"_id": str(item)}, doc, upsert=True)
        return self._clone(doc)

    def delete_item(self, item: str, partition_key: Any = None):
        self.collection.delete_one({"_id": str(item)})

    def upsert_item(self, body: Dict[str, Any]):
        doc = self._normalize_doc(body)
        self.collection.replace_one({"_id": doc["_id"]}, doc, upsert=True)
        return self._clone(doc)

    def query_items(
        self,
        query: Optional[str] = None,
        parameters: Optional[Iterable[Dict[str, Any]]] = None,
        enable_cross_partition_query: bool = False,
    ):
        if not query:
            return list(self.collection.find())

        if isinstance(query, dict):
            return list(self.collection.find(query))

        filter_doc = self._parse_filter(query, parameters)
        return list(self.collection.find(filter_doc))


def _build_mongo():
    if not MONGO_URI or not MONGO_DATABASE:
        raise RuntimeError("MONGO_URI and MONGO_DATABASE must be configured")

    client = MongoClient(
        MONGO_URI,
        tlsCAFile=certifi.where(),
        serverSelectionTimeoutMS=10000,
    )
    database = client[MONGO_DATABASE]
    existing_collections = set(database.list_collection_names())

    for collection_name in REQUIRED_COLLECTIONS.values():
        if collection_name in existing_collections:
            continue

        try:
            database.create_collection(collection_name)
            existing_collections.add(collection_name)
        except CollectionInvalid:
            existing_collections.add(collection_name)

    return {
        container_key: MongoCollectionAdapter(database[collection_name])
        for container_key, collection_name in REQUIRED_COLLECTIONS.items()
    }


def _build_memory():
    database = InMemoryDatabase()
    return {
        container_key: database.create_container_if_not_exists(collection_name)
        for container_key, collection_name in REQUIRED_COLLECTIONS.items()
    }


def _env_configured() -> bool:
    return bool(MONGO_URI and MONGO_DATABASE and not MONGO_URI.startswith("<") and not MONGO_DATABASE.startswith("<"))


try:
    if _env_configured():
        containers = _build_mongo()
    else:
        raise RuntimeError("MONGO_URI/MONGO_DATABASE are not configured")
except Exception as exc:  # pragma: no cover - local fallback
    print(f"[database] Using in-memory fallback datastore: {exc}")
    containers = _build_memory()

checkpoints_container = containers["checkpoints_container"]
users_container = containers["users_container"]
stores_container = containers["stores_container"]
tags_container = containers["tags_container"]
settings_container = containers["settings_container"]
scan_container = containers["scan_container"]
alerts_container = containers["alerts_container"]
rounds_container = containers["rounds_container"]
audit_logs_container = containers["audit_logs_container"]
reports_container = containers["reports_container"]
