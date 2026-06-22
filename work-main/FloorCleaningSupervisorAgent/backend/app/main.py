from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import MONGO_DATABASE
from app.core.database import users_container
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
