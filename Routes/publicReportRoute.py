from typing import Optional

from fastapi import APIRouter, Body, Request, UploadFile
from openai import images

from Models.PublicReport import PublicReportModel, PublicReportUpdateModel
from Services import publicReportService
from Services.common import save_multiple_files

router = APIRouter(tags=["PUBLIC REPORT MANAGEMENT"])


@router.post("/public-reports/")
async def create_public_report(
    public_report: PublicReportModel = Body(...),
    images: Optional[list[UploadFile]] = None,
):
    if images is not None and images != "":
        file = await save_multiple_files(images, "uploads/public_reports")
        public_report.images = file
    return publicReportService.create_public_report(public_report)


@router.get("/public-reports/{page}")
def get_public_reports(
    request: Request,
    page: int,
    limit: int = 10,
    status: Optional[int] = None,
    search_query: Optional[str] = None,
):
    return publicReportService.get_public_reports(request, page, limit, status, search_query)


@router.get("/public-report/{public_report_id}")
def get_public_report(request: Request, public_report_id: str):
    return publicReportService.get_public_report_by_id(request, public_report_id)


@router.put("/public-report/{public_report_id}")
async def update_public_report(
    public_report_id: str,
    public_report: PublicReportUpdateModel = Body(...),
    images: Optional[list[UploadFile]] = None,
):
    if images is not None and images != "":
        file = await save_multiple_files(images, "uploads/public_reports")
        public_report.images = file
    return publicReportService.update_public_report(public_report_id, public_report)


@router.delete("/public-report/{public_report_id}")
def delete_public_report(public_report_id: str, deleted_by: Optional[str] = None):
    return publicReportService.delete_public_report(public_report_id, deleted_by)
