from app.core.database import settings_container

def get_settings(store_id:str):

    return settings_container.read_item(
        item=store_id,
        partition_key=store_id
    )

def update_settings(
        store_id:str,
        gps_required:bool,
        fraud_detection:bool,
        duplicate_block:bool,
        push_alerts:bool
):
    settings={
        "id":store_id,
        "gps_required":gps_required,
        "fraud_detection":fraud_detection,
        "duplicate_block":duplicate_block,
        "push_alerts":push_alerts
    }
    settings_container.upsert_items(settings)

    return{
        "message":"Settings updated"
    }