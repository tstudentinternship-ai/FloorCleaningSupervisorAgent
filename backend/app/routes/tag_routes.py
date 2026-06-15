from fastapi import APIRouter

from app.schemas.tag_schema import(
    RegisterTagRequest,
    AssignTagRequest
)

from app.services.tag_service import(
    register_tag,
    get_tags,
    assign_tag_location,
    reset_tags,
    get_tag_stats
)

router=APIRouter(
    prefix="/tags",
    tags=["Tags"]
)

@router.post("/register")
def create_tag(
    payload:RegisterTagRequest
):
    return register_tag(
        payload.store_id,
        payload.nfc_tag_uid
    )

@router.get("")
def fetch_tags(store_id:str):
    return get_tags(store_id)

@router.put("/{tag_id}/assign")
def assign_location(
    tag_id:str,
    payload:AssignTagRequest
):
    return assign_tag_location(
        tag_id,
        payload.store_id,
        payload.location
    )

@router.delete("/reset/{store_id}")
def delete_tags(store_id:str):
    return reset_tags(store_id)

@router.get("/stats/{store_id}")
def fetch_stats(store_id:str):
    return get_tag_stats(store_id)