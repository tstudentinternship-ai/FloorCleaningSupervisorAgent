from pydantic import BaseModel

class RegisterTagRequest(BaseModel):
    store_id:str
    nfc_tag_uid:str

class AssignTagRequest(BaseModel):
    store_id:str
    location:str

class TagResponse(BaseModel):
    id:str
    store_id:str
    nfc_tag_uid:str
    location:str
    status:str

