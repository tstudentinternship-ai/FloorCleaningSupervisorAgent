import uuid
from datetime import datetime

from app.core.database import tags_container

def register_tag(
        store_id:str,
        nfc_tag_uid:str
):
    tag={
        "id":str(uuid.uuid4()),
        "store_id":store_id,
        "nfc_tag_uid":nfc_tag_uid,
        "location":"",
        "status":"unassigned",
        "registered_at":datetime.utcnow().isoformat()
    }
    tags_container.create_item(tag)

    return tag

def get_tags(store_id:str):

    query="""
    SELECT * FROM c where c.store_id=@store_id
    """

    parameters=[
        {
            "name":"@store_id",
            "value":store_id
        }
    ]

    return list(
        tags_container.query_items(
            query=query,
            parameters=parameters,
            enable_cross_partition_query=True
        )
    )

def assign_tag_location(
        tag_id:str,
        store_id:str,
        location:str
):
    tag=tags_container.read_item(
        item=tag_id,
        partition_key=store_id
    )

    tag["location"]=location
    tag["status"]="active"

    tags_container.replace_item(
        item=tag_id,
        body=tag
    )

    return{
        "message":"Location assigned"
    }

def reset_tags(store_id:str):
    tags=get_tags(store_id)

    for tag in tags:
        tags_container.delete_item(
            item=tag["id"],
            partition_key=store_id
        )
    
    return{
        "message": "All tags removed"
    }

def get_tag_stats(store_id:str):
    tags=get_tags(store_id)

    registered=len([
        t for t in tags
        if t["status"]=="active"
    ])

    unregistered=len([
        t for t in tags
        if t["status"] == "unassigned"
    ])

    errors = len([
        t for t in tags
        if t["status"] == "error"
    ])

    return {
        "registered":registered,
        "unregistered":unregistered,
        "errors":errors
    }