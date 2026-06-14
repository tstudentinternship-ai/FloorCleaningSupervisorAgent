from pydantic import BaseModel

class RegistrationReviewResponse(BaseModel):
    checkpoint_id: str
    checkpoint_name: str
    nfc_tag_uid: str
    gps_lat: float
    gps_lon: float
    radius: int
    deployement_status: str
    is_active: bool
    