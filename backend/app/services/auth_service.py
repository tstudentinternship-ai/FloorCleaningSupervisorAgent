from app.core.database import users_container
from passlib.context import CryptContext

pwd_context=CryptContext(schemes=["bcrypt"], deprecated="auto")

def register_user(data):

    query = f"SELECT * FROM c WHERE c.user_id='{data.user_id}'"
    items = list(users_container.query_items(
        query=query,
        enable_cross_partition_query=True
    ))

    if items:
        return{
            "status": "error",
            "message": "User already exists"
        }

    user_document = {
        "id": data.user_id,
        "user_id": data.user_id,
        "name": data.name,
        "email": data.email,
        "password_hash": pwd_context.hash(data.password),
        "role": data.role,
        "store_id": data.store_id
    }

    users_container.create_item(body=user_document)

    return{
        "status": "success",
        "message": "User registered successfully"
    }

def login_user(data):
        
    query = f"SELECT * FROM c WHERE c.user_id = '{data.user_id}'"

    items = list(users_container.query_items(
        query=query,
        enable_cross_partition_query=True
    ))

    if not items:
        return{
            "status": "error",
            "message": "User not found"
        }

    user = items[0]

    if not pwd_context.verify(
        data.password,
        user["password_hash"]
    ):

        return{
            "status": "error",
            "message": "Invalid password"
        }

    if user["role"] != data.role:
        return{
            "status": "error",
            "message": "Invalid role selected"
        }

    return{
        "status": "success",
        "user_id": user["user_id"],
        "name": user["name"],
        "role": user["role"],
        "store_id": user["store_id"]
    }
    