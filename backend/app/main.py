from fastapi import FastAPI 
from app.routes import scan_routes
from app.core.database import checkpoints_container

app=FastAPI()

app.include_router(scan_routes.router)

@app.get("/test-db")
def test_db():
    try:
        items=list(checkpoints_container.read_all_items())
        return {"status": "connected","count":len(items)}
    except Exception as e:
        return {"error":str(e)}