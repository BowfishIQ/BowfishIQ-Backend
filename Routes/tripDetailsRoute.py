from typing import Literal, Optional

from fastapi import APIRouter, Body, Depends, Path, Query, UploadFile

from Models.TripDetails import TripDetailsModel, TripDetailsUpdateModel, UserTripFilters
from Models.TripAnalysis import TripAnalysisResponse
from Services import tripDetailsService
from Services import userTripService
from Services import tripLogbookService
from Services import tripDetailViewService
from Services import tripAnalysisService
from Services import tripCoastalConditionsService
from Services.common import save_multiple_files

router = APIRouter(tags=["TRIP DETAILS MANAGEMENT"])


@router.post("/trip-details/coastal-conditions", tags=["TRIP PAGE"])
def capture_trip_coastal_conditions(
    trip_id: str = Query(..., min_length=1),
    action: Literal["recapture_start", "capture_end"] = Query(...),
):
    """Capture current coastal conditions in the selected START or END slot.

    Uses saved map coordinates, then resolves coastal area names, UUIDs or record IDs.
    If a saved coastal region has no coordinates, uses a clearly marked NOAA regional
    reference station in that state; these are regional conditions, not boat coordinates.
    Each action replaces only its selected snapshot in a separate collection.
    Capture times are current UTC times, not historical trip date/time backfills.
    Values are station observations within 50 km of the resolved coordinate/reference
    station, not measurements at the boat. The response identifies the coordinate basis.
    Next high/low tides are predictions in feet relative to MLLW. Stale/flagged
    observations and unsupported wave heights remain null, with reasons.
    """
    return tripCoastalConditionsService.capture_conditions(trip_id, action)


@router.get("/trip-details/coastal-conditions", tags=["TRIP PAGE"])
def get_trip_coastal_conditions(trip_id: str = Query(..., min_length=1)):
    """Read saved START/END snapshots without refreshing them or calling providers."""
    return tripCoastalConditionsService.get_conditions(trip_id)


@router.post("/trip-details/ai-analysis", response_model=TripAnalysisResponse, tags=["TRIP PAGE"])
def generate_trip_analysis(trip_id: str = Query(..., min_length=1)):
    """Generate/regenerate AI Trip Analysis for one trip using only trip_id.

    Each call generates a fresh analysis using the configured OpenAI key. It does
    not update the saved trip. Numeric metrics and anonymous comparisons are
    calculated by the server, with earlier logs as baselines. Missing data stays
    unavailable. The trip IQ score is an AI assessment, not a measured index.
    """
    return tripAnalysisService.get_trip_analysis(trip_id)


@router.get("/get-trip-details-by-trip-id", tags=["TRIP PAGE"])
def get_trip_details_by_trip_id(trip_id: str = Query(..., min_length=1)):
    """Display details for one saved trip, with model codes converted to text.

    Excludes AI Trip Analysis and Coastal conditions. Missing ratings, automatic
    weather/moon data, species families and individual fish attribution are not
    inferred. Seen fish = shot fish + fish seen but not shot. Overnight times
    assume the end is on the following day; shooter rates use full trip duration.
    """
    return tripDetailViewService.get_trip_details_by_trip_id(trip_id)


@router.get("/get-trip-details-by-user-id-and-category", tags=["TRIP PAGE"])
def get_trip_details_by_user_id_and_category(
    userid: str = Query(..., min_length=1),
    water_type: Literal["inland", "coastal", "both"] = Query(...),
):
    """Logbook totals, all trips, and location history; excludes boat planning.

    Inland includes water types 1/2/3, coastal includes 4, and both includes 1/2/3/4.
    Includes owned trips and trips joined as active crew. Ratings are null because
    trip logs do not currently store a star rating. All totals use the selected category.
    """
    return tripLogbookService.get_trip_details_by_user_id_and_category(
        userid, water_type
    )


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
