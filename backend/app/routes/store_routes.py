from fastapi import APIRouter

from app.schemas.store_schema import StoreConfigUpdate

from app.services.store_service import (
    get_all_stores,
    get_store,
    update_store_config
)

router=APIRouter(
    prefix="/stores",
    tags=["Stores"]
)

@router.get("")
def fetch_stores():
    return get_all_stores()

@router.get("/{store_id}")
def fetch_store(store_id:str):
    return get_store(store_id)

@router.put("/{store_id}/config")
def update_config(
    store_id:str,
    payload:StoreConfigUpdate
):
    return update_store_config(
        store_id,
        payload.daily_rounds,
        payload.checkpoint_count
    )