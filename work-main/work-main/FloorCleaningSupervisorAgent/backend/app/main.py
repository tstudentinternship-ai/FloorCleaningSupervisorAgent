from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import MONGO_DATABASE
from app.core.database import users_container
from app.schemas.auth_schema import RegisterRequest
from app.services.auth_service import register_user, list_users
from app.routes import (
    alert_routes,
    audit_routes,
    auth_routes,
    checkpoint_routes,
    dashboard_routes,
    report_routes,
    review_routes,
    scan_routes,
    settings_routes,
    store_routes,
    tag_routes,
    user_routes,
)

print("MAIN.PY LOADED")
print("FILE =", Path(__file__).resolve())

app = FastAPI(title="Abhishek API")

@app.on_event("startup")
def seed_default_admin():
    try:
        users = list_users()
        if not users:
            print("[startup] No users found. Seeding default admin user (USR_001)")
            admin_data = RegisterRequest(
                user_id="USR_001",
                name="Admin User",
                email="admin@cleancheck.com",
                password="password123",
                role="admin",
                store_id=None
            )
            register_user(admin_data)
    except Exception as e:
        print(f"[startup] Seeding failed: {e}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[],
    allow_origin_regex=".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.include_router(auth_routes.router)
app.include_router(user_routes.router)
app.include_router(store_routes.router)
app.include_router(tag_routes.router)
app.include_router(checkpoint_routes.router)
app.include_router(review_routes.router)
app.include_router(scan_routes.router)
app.include_router(alert_routes.router)
app.include_router(dashboard_routes.router)
app.include_router(report_routes.router)
app.include_router(settings_routes.router)
app.include_router(audit_routes.router)
@app.get("/cors-test")
def cors_test():
    return {"message": "cors working"}
@app.get("/abc123")
def abc123():
    return {"test": "working"}
@app.get("/test-db")
def test_db():
    try:
        if hasattr(users_container, "collection"):
            db_name = users_container.collection.database.name
            collection_name = users_container.collection.name
            count = users_container.collection.count_documents({})
        else:
            db_name = MONGO_DATABASE or "in-memory"
            collection_name = getattr(users_container, "id", "users")
            count = len(list(users_container.read_all_items()))

        return {
            "status": "connected",
            "database": db_name,
            "collection": collection_name,
            "count": count,
        }
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "database": MONGO_DATABASE or "not-configured",
                "message": str(exc),
            },
        )
