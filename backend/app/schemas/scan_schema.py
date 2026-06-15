from pydantic import BaseModel

class ScanRequest(BaseModel):
    nfc_tag_uid: str 
    device_timestamp: str
    gps_lat: float
    gps_lon: float
    gps_accuracy: float
    shift_date: str