from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
import os
from app.schemas.reports import ReportRequest, ReportResponse
from app.services.report_service import ReportService
from app.core.security import get_current_user_id

router = APIRouter()
_report_service = ReportService()

@router.post("/generate", response_model=ReportResponse)
async def generate_report(
    req: ReportRequest,
    current_user_id: str = Depends(get_current_user_id)
):
    """Generates a professional astrology PDF report."""
    return await _report_service.generate_report(
        profile_id=req.profile_id,
        report_type=req.type,
        language=req.language
    )

@router.get("/download/{filename}")
async def download_report(filename: str):
    """Downloads a generated PDF report."""
    filepath = os.path.join("storage/reports", filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(filepath, media_type="application/pdf", filename=filename)
