from pydantic import BaseModel

class CheckpointCreate(BaseModel):
    id: str
    store_id: str
    name: str
    nfc_tag_uid: str
    gps_lat: float
    gps_lon: float
    registered_by: str