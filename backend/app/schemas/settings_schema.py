from pydantic import BaseModel

class SettingsUpdate(BaseModel):
    gps_required:bool
    fraud_detection:bool
    duplicate_block:bool
    push_alerts:bool