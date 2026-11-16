from typing import Optional

from fastapi import APIRouter, Body, Query

from Models.Lakes import LakesModel, LakesUpdateModel
from Services import lakesService

router = APIRouter(tags=["LAKE MANAGEMENT"])


@router.post("/lakes/")
def create_lake(lake: LakesModel = Body(...)):
    return lakesService.create_lake(lake)


@router.get("/lakes/{page}")
def get_lakes(
    page: int,
    limit: int = 10,
    status: Optional[int] = None,
    search_query: Optional[str] = None,
    user_id: Optional[str] = None,
):
    return lakesService.get_lakes(page, limit, status, search_query, user_id)


@router.get("/lake/{lake_id}")
def get_lake(lake_id: str, user_id: Optional[str] = None):
    return lakesService.get_lake_by_id(lake_id, user_id)


@router.put("/lake/{lake_id}")
def update_lake(
    lake_id: str,
    lake: LakesUpdateModel = Body(...),
    user_id: str = Query(..., min_length=1, pattern=r"\S"),
):
    return lakesService.update_lake(lake_id, lake, user_id)


@router.delete("/lake/{lake_id}")
def delete_lake(
    lake_id: str,
    user_id: str = Query(..., min_length=1, pattern=r"\S"),
):
    return lakesService.delete_lake(lake_id, user_id)
