from pydantic import BaseModel

class RegisterRequest(BaseModel):

    user_id: str
    name: str
    email: str
    password: str
    role: str
    store_id: str

class LoginRequest(BaseModel):

    user_id: str
    password_hash: str
    role: str