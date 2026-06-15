from fastapi import APIRouter
from app.schemas.scan_schema import ScanRequest
from app.services.scan_service import process_scan

router = APIRouter()

@router.post("/scan")

def scan(data: ScanRequest):
    return process_scan(data)