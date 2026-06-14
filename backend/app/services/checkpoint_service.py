from app.core.database import checkpoints_container
from datetime import datetime

def create_checkpoint(data):

    item = {
        "id": data.id,
        "store_id": data.store_id,
        "name": data.name,
        "nfc_tag_uid": data.nfc_tag_uid,
        "gps_lat": data.gps_lat,
        "gps_lon": data.gps_lon,
        "registered_at": datetime.utcnow().isoformat(),
        "registered_by": data.registered_by
    }

    checkpoints_container.create_item(item)

    return {
        "message": "Checkpoint registered successfully"
    }