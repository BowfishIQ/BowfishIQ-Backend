from typing import Optional

from fastapi import APIRouter, Body, Query

from Models.BoatRamp import BoatRampModel, BoatRampUpdateModel
from Services import boatRampService

router = APIRouter(tags=["BOAT RAMP MANAGEMENT"])


@router.post("/boat-ramps/")
def create_boat_ramp(boat_ramp: BoatRampModel = Body(...)):
    return boatRampService.create_boat_ramp(boat_ramp)


@router.get("/boat-ramps/{page}")
def get_boat_ramps(
    page: int,
    limit: int = 10,
    status: Optional[int] = None,
    search_query: Optional[str] = None,
    user_id: Optional[str] = None,
):
    return boatRampService.get_boat_ramps(page, limit, status, search_query, user_id)


@router.get("/boat-ramp/{boat_ramp_id}")
def get_boat_ramp(boat_ramp_id: str, user_id: Optional[str] = None):
    return boatRampService.get_boat_ramp_by_id(boat_ramp_id, user_id)


@router.put("/boat-ramp/{boat_ramp_id}")
def update_boat_ramp(
    boat_ramp_id: str,
    boat_ramp: BoatRampUpdateModel = Body(...),
    user_id: str = Query(..., min_length=1, pattern=r"\S"),
):
    return boatRampService.update_boat_ramp(boat_ramp_id, boat_ramp, user_id)


@router.delete("/boat-ramp/{boat_ramp_id}")
def delete_boat_ramp(
    boat_ramp_id: str,
    user_id: str = Query(..., min_length=1, pattern=r"\S"),
):
    return boatRampService.delete_boat_ramp(boat_ramp_id, user_id)
