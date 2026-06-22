from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.core.database import alerts_container, checkpoints_container, rounds_container, scan_container, stores_container, tags_container, users_container
from app.services.alert_service import get_alert_summary, list_alerts
from app.services.scan_service import get_scan_history, get_scan_stats
from app.services.tag_service import get_tag_stats


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", ""))
    except Exception:
        return None


def _safe_store(store: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": store.get("id"),
        "name": store.get("name"),
        "storeNumber": store.get("storeNumber"),
        "location": store.get("location"),
        "manager": store.get("manager"),
        "compliance": store.get("compliance", 0),
        "nfcCount": store.get("nfcCount", 0),
        "activeAlerts": store.get("activeAlerts", 0),
        "lastSync": store.get("lastSync"),
        "daily_rounds": store.get("daily_rounds", 3),
        "checkpoint_count": store.get("checkpoint_count", 0),
        "round_duration_minutes": store.get("round_duration_minutes", 90),
        "duplicate_window_minutes": store.get("duplicate_window_minutes", 30),
        "complianceHistory": store.get("complianceHistory"),
    }


def _hour_bucket(dt: datetime) -> str:
    if not hasattr(dt, "strftime"):
        return ""
    bucket = dt.strftime("%I%p")
    return bucket.lstrip("0")


def _hour_sort_key(hour_label: str) -> int:
    label = hour_label.strip().upper()
    if not label:
        return 0
    suffix = 12 if label.endswith("PM") else 0
    hour_text = label[:-2]
    try:
        hour = int(hour_text)
    except ValueError:
        return 0
    if hour == 12:
        hour = 0
    return hour + suffix


def _bucket_scans(scans: List[Dict[str, Any]]):
    grouped: Dict[str, Dict[str, int]] = defaultdict(lambda: {"done": 0, "missed": 0})
    for scan in scans:
        dt = _parse_dt(scan.get("server_timestamp")) or _parse_dt(scan.get("device_timestamp"))
        if not dt:
            continue
        bucket = _hour_bucket(dt)
        if scan.get("scan_status") == "verified":
            grouped[bucket]["done"] += 1
        else:
            grouped[bucket]["missed"] += 1
    return [{"hour": hour, **values} for hour, values in sorted(grouped.items(), key=lambda item: _hour_sort_key(item[0]))]


def _store_rounds(store_id: str):
    rounds = list(
        rounds_container.query_items(
            query="SELECT * FROM c WHERE c.store_id=@store_id",
            parameters=[{"name": "@store_id", "value": store_id}],
            enable_cross_partition_query=True,
        )
    )
    rounds.sort(key=lambda item: item.get("time") or item.get("startTime") or "", reverse=True)
    return rounds


def _round_to_view(round_item: Dict[str, Any], active: bool = False):
    scans = round_item.get("scans", []) or []
    checkpoint_items = [
        {
            "id": scan.get("id"),
            "location": scan.get("location"),
            "zone": scan.get("zone"),
            "uid": scan.get("nfcUid") or scan.get("nfc_tag_uid"),
            "status": scan.get("status") or scan.get("scan_status"),
            "scannedAt": scan.get("scannedAt") or scan.get("time"),
        }
        for scan in scans
    ]
    return {
        "id": round_item.get("id"),
        "name": round_item.get("name"),
        "time": round_item.get("time"),
        "staff": round_item.get("staff") or round_item.get("employee_name"),
        "compliance": round_item.get("compliance", 0),
        "totalScans": round_item.get("totalScans", len(checkpoint_items)),
        "completedScans": round_item.get("completedScans", len([scan for scan in scans if (scan.get("status") or scan.get("scan_status")) == "verified"])),
        "isActive": active or round_item.get("status") == "active",
        "checkpointItems": checkpoint_items,
        "status": round_item.get("status", "completed"),
    }


def _store_alerts(store_id: str):
    alerts = list_alerts(store_id=store_id)
    return alerts


def _stale_time(scans: List[Dict[str, Any]]):
    if not scans:
        return "No scan activity"
    latest = _parse_dt(scans[0].get("server_timestamp") or scans[0].get("time"))
    if not latest:
        return None
    minutes = int((datetime.utcnow() - latest).total_seconds() / 60)
    return f"{minutes}m" if minutes else "just now"


def _compliance_from_scans(scans: List[Dict[str, Any]]) -> int:
    if not scans:
        return 0
    verified = len([scan for scan in scans if scan.get("scan_status") == "verified"])
    return round((verified / len(scans)) * 100)


def _compliance_history_from_scans(scans: List[Dict[str, Any]]):
    return _bucket_scans(scans)


def global_dashboard():
    stores = [_safe_store(store) for store in stores_container.read_all_items()]
    for store in stores:
        store_scans = get_scan_history(store["id"])
        store["compliance"] = store.get("compliance") or _compliance_from_scans(store_scans)
        store["nfcCount"] = len(list(tags_container.query_items(query="SELECT * FROM c WHERE c.store_id=@store_id", parameters=[{"name": "@store_id", "value": store["id"]}], enable_cross_partition_query=True)))
        store["activeAlerts"] = len([alert for alert in list_alerts(store_id=store["id"]) if not alert["reviewed"]])
        store["lastSync"] = _stale_time(store_scans)

    all_scans = list(scan_container.read_all_items())
    all_alerts = list_alerts()
    stats = {
        "stores": len(stores),
        "tags": len(list(tags_container.read_all_items())),
        "alerts": len(all_alerts),
        "compliance": round(sum(store["compliance"] for store in stores) / max(len(stores), 1)) if stores else 0,
    }
    return {
        "stats": stats,
        "stores": stores,
        "alert_summary": get_alert_summary(),
        "compliance_history": _compliance_history_from_scans(all_scans),
        "recent_alerts": all_alerts[:10],
    }


def store_dashboard(store_id: str):
    store = next((s for s in stores_container.read_all_items() if s.get("id") == store_id), None)
    if not store:
        return None

    store = _safe_store(store)
    scans = get_scan_history(store_id)
    alerts = _store_alerts(store_id)
    rounds = _store_rounds(store_id)
    tag_stats = get_tag_stats(store_id)
    scan_stats = get_scan_stats(store_id)
    store["compliance"] = store.get("compliance") or _compliance_from_scans(scans)
    store["nfcCount"] = len(list(tags_container.query_items(query="SELECT * FROM c WHERE c.store_id=@store_id", parameters=[{"name": "@store_id", "value": store_id}], enable_cross_partition_query=True)))
    store["activeAlerts"] = len([alert for alert in alerts if not alert["reviewed"]])
    store["lastSync"] = _stale_time(scans)

    return {
        "store": store,
        "tag_stats": tag_stats,
        "scan_stats": scan_stats,
        "alert_summary": get_alert_summary(store_id),
        "compliance_history": _compliance_history_from_scans(scans),
        "rounds": rounds,
        "alerts": alerts,
        "stale_time": _stale_time(scans),
    }


def _store_checkpoints(store_id: str) -> List[Dict[str, Any]]:
    """Return all active/deployed checkpoints for a store."""
    items = list(
        checkpoints_container.query_items(
            query="SELECT * FROM c WHERE c.store_id=@store_id",
            parameters=[{"name": "@store_id", "value": store_id}],
            enable_cross_partition_query=True,
        )
    )
    return [item for item in items if item.get("is_active") or item.get("deployment_status") == "deployed"]


def _build_checkpoint_items(
    store_checkpoints: List[Dict[str, Any]],
    scanned_uids: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Merge registered checkpoints with scan history to produce checkpoint items."""
    result = []
    for cp in store_checkpoints:
        uid = cp.get("nfc_tag_uid", "")
        scan = scanned_uids.get(uid)
        result.append({
            "id": cp.get("id"),
            "location": cp.get("name"),
            "zone": cp.get("zone"),
            "uid": uid,
            "status": scan.get("scan_status", "pending") if scan else "pending",
            "scannedAt": scan.get("server_timestamp") if scan else None,
        })
    return result


def cleaner_dashboard(user_id: str):
    user = next((u for u in users_container.read_all_items() if u.get("user_id") == user_id), None)
    if not user:
        return None

    store_id = user.get("store_id")
    store = next((s for s in stores_container.read_all_items() if s.get("id") == store_id), None) if store_id else None
    scans = get_scan_history(store_id) if store_id else []
    rounds = _store_rounds(store_id) if store_id else []
    active_round = next((r for r in rounds if r.get("status") == "active"), None)
    completed_rounds = [round_item for round_item in rounds if round_item.get("status") != "active"]
    alerts = _store_alerts(store_id) if store_id else []

    # Build checkpoint items from the checkpoint registry, merged with today's scans.
    # This ensures the cleaner sees ALL checkpoints, not just ones already scanned.
    store_checkpoints: List[Dict[str, Any]] = _store_checkpoints(store_id) if store_id else []
    today = datetime.utcnow().strftime("%Y-%m-%d")
    todays_scans = [s for s in scans if (s.get("shift_date") or s.get("server_timestamp", ""))[:10] == today]
    # Map uid -> most recent scan for today
    scanned_uids: Dict[str, Dict[str, Any]] = {}
    for s in sorted(todays_scans, key=lambda x: x.get("server_timestamp", "")):
        uid = s.get("nfc_tag_uid", "")
        if uid:
            scanned_uids[uid] = s

    checkpoint_items = _build_checkpoint_items(store_checkpoints, scanned_uids)
    daily_rounds = int((store or {}).get("daily_rounds", 3))

    # If there is an active round, attach the full checkpoint items list to it.
    # If no active round, build a virtual current round from today's scan data.
    if active_round is not None:
        current_round_view = _round_to_view(active_round, active=True)
        # Always override checkpointItems with the registry-based list
        current_round_view["checkpointItems"] = checkpoint_items
        current_round_view["totalScans"] = len(store_checkpoints) or current_round_view.get("totalScans", 0)
        current_round_view["completedScans"] = len([c for c in checkpoint_items if c["status"] == "verified"])
    elif store_checkpoints:
        # No active round yet — present a virtual "Round 1" so the cleaner sees their checkpoints
        current_round_view: Optional[Dict[str, Any]] = {
            "id": None,
            "name": "Round 1",
            "time": None,
            "staff": user.get("name"),
            "compliance": 0,
            "totalScans": len(store_checkpoints),
            "completedScans": 0,
            "isActive": True,
            "checkpointItems": checkpoint_items,
            "status": "active",
        }
    else:
        current_round_view = None

    compliance_history = store.get("complianceHistory") if store and store.get("complianceHistory") else _bucket_scans(scans)
    stats = {
        "today_scans": len(scans),
        "today_compliance": _compliance_from_scans(scans),
        "active_alerts": len([alert for alert in alerts if not alert["reviewed"]]),
        "completed_rounds": len(completed_rounds),
        "daily_rounds": daily_rounds,
    }

    return {
        "user": {
            "user_id": user.get("user_id"),
            "name": user.get("name"),
            "username": user.get("username"),
            "role": user.get("role"),
            "store_id": store_id,
            "shift_start": user.get("shift_start"),
            "shift_end": user.get("shift_end"),
            "joined_at": user.get("joined_at"),
        },
        "store": _safe_store(store) if store else None,
        "current_round": current_round_view,
        "completed_rounds": [_round_to_view(round_item) for round_item in completed_rounds],
        "compliance_history": compliance_history,
        "stats": stats,
        "alerts": alerts,
    }
