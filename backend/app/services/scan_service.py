from app.core.database import checkpoints_container,scan_container
from datetime import datetime
import uuid

def process_scan(data):
    query = f"SELECT * FROM WHERE c.nfc_tag_uid=`{data.nfc_tag_uid}`"
    items = list(checkpoints_container.query_items(query,enable_cross_partition_query=True))

    if not items:
        return {"status":"unregistered_tag"}

    checkpoint = items[0]

    item = {
        "id": str(uuid.uuid4()),
        "store_id": checkpoint["store_id"],
        "checkpoint_id": checkpoint["id"],
        "nfc_tag_uid": data.nfc_tag_uid,
        "server_timestamp": datetime.utcnow().isoformat(),
        "device_timestamp": data.device_timestamp,
        "gps_lat": data.gps_lat,
        "gps_lon": data.gps_lon,
        "gps_accuracy": data.gps_accuracy,
        "shift_data": data.shift_date,
        "compliance_status": "on_time"
    }

    scan_container.create_item(item)
    return {"status":"success"}