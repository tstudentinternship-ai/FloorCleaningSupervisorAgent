from pydantic import BaseModel

class StoreConfigUpdate(BaseModel):
    daily_rounds:int
    checkpoint_count:int

class StoreResponse(BaseModel):
    id:str
    name:str
    location:str
    daily_rounds:int
    checkpoint_count:int