from typing import Optional

from fastapi import APIRouter, Body, Depends, Path, Query, UploadFile

from Models.TripDetails import TripDetailsModel, TripDetailsUpdateModel, UserTripFilters
from Services import tripDetailsService
from Services import userTripService
from Services.common import save_multiple_files

router = APIRouter(tags=["TRIP DETAILS MANAGEMENT"])


@router.get("/users/{user_id}/trip-details")
def get_user_trip_details(
    user_id: str = Path(..., min_length=1),
    filters: UserTripFilters = Depends(),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=100),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
):
    """Paginated owned/crew trips, sorted by trip date. Omit dates for all days."""
    return userTripService.get_user_trip_details(
        user_id, filters, page, limit, sort_order
    )


@router.get("/users/{user_id}/trip-details/summary")
def get_user_trip_summary(
    user_id: str = Path(..., min_length=1),
    filters: UserTripFilters = Depends(),
):
    """Counts over every matching trip, independent of list pagination."""
    return userTripService.get_user_trip_summary(user_id, filters)


@router.post("/trip-details/")
async def create_trip_details(
    trip_details: TripDetailsModel = Body(...),
    images: Optional[list[UploadFile]] = None,
):
    if images:
        uploaded = await save_multiple_files(images, "uploads/trip_details")
        trip_details.images = (trip_details.images or []) + uploaded
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
async def update_trip_details(
    trip_details_id: str,
    trip_details: TripDetailsUpdateModel = Body(...),
    images: Optional[list[UploadFile]] = None,
):
    if images:
        # Verify the trip before writing files. The service also checks the write result.
        existing = tripDetailsService.get_trip_details_by_id(trip_details_id)
        if existing["status"] != "success":
            return existing
        uploaded = await save_multiple_files(images, "uploads/trip_details")
        retained = (
            trip_details.images
            if "images" in trip_details.model_fields_set
            else existing["data"].get("images")
        )
        trip_details.images = (retained or []) + uploaded
    return tripDetailsService.update_trip_details(trip_details_id, trip_details)


@router.delete("/trip-detail/{trip_details_id}")
def delete_trip_details(trip_details_id: str, deleted_by: Optional[str] = None):
    return tripDetailsService.delete_trip_details(trip_details_id, deleted_by)
