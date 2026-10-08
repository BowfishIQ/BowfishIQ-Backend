from typing import Optional

from fastapi import APIRouter, Body

from Models.TripDetails import TripDetailsModel, TripDetailsUpdateModel
from Services import tripDetailsService

router = APIRouter(tags=["TRIP DETAILS MANAGEMENT"])


@router.post("/trip-details/")
def create_trip_details(trip_details: TripDetailsModel = Body(...)):
    return tripDetailsService.create_trip_details(trip_details)


@router.get("/trip-details/{page}")
def get_trip_details(
    page: int,
    limit: int = 10,
    status: Optional[int] = None,
    search_query: Optional[str] = None,
    user_id: Optional[str] = None,
):
    return tripDetailsService.get_trip_details(
        page, limit, status, search_query, user_id
    )


@router.get("/trip-detail/{trip_details_id}")
def get_trip_details_by_id(trip_details_id: str):
    return tripDetailsService.get_trip_details_by_id(trip_details_id)


@router.put("/trip-detail/{trip_details_id}")
def update_trip_details(
    trip_details_id: str,
    trip_details: TripDetailsUpdateModel = Body(...),
):
    return tripDetailsService.update_trip_details(trip_details_id, trip_details)


@router.delete("/trip-detail/{trip_details_id}")
def delete_trip_details(trip_details_id: str, deleted_by: Optional[str] = None):
    return tripDetailsService.delete_trip_details(trip_details_id, deleted_by)
