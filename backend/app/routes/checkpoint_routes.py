from fastapi import APIRouter
print("checkpoint_routes imported")
from app.schemas.checkpoint_schema import CheckpointCreate
from app.services.checkpoint_service import create_checkpoint

router = APIRouter()

@router.post("/checkpoints")
def register_checkpoint(data: CheckpointCreate):
    return create_checkpoint(data)
print("Router routes =", router.routes)