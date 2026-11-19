from typing import Optional

from fastapi import APIRouter, Body, Query

from Models.Coastal import CoastalModel, CoastalUpdateModel
from Services import coastalService

router = APIRouter(tags=["COASTAL MANAGEMENT"])


@router.post("/coastals/")
def create_coastal(coastal: CoastalModel = Body(...)):
    return coastalService.create_coastal(coastal)


@router.get("/coastals/{page}")
def get_coastals(
    page: int, limit: int = 10, status: Optional[int] = None,
    search_query: Optional[str] = None, state: Optional[str] = None,
):
    return coastalService.get_coastals(page, limit, status, search_query, state)


@router.get("/coastal/{coastal_id}")
def get_coastal(coastal_id: str):
    return coastalService.get_coastal_by_id(coastal_id)


@router.put("/coastal/{coastal_id}")
def update_coastal(coastal_id: str, coastal: CoastalUpdateModel = Body(...)):
    return coastalService.update_coastal(coastal_id, coastal)


@router.delete("/coastal/{coastal_id}")
def delete_coastal(
    coastal_id: str, user_id: str = Query(..., min_length=1, pattern=r"\S"),
):
    return coastalService.delete_coastal(coastal_id, user_id)
