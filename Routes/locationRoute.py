from typing import Literal, Optional

from fastapi import APIRouter, Body, Query, Request

import Services.locationService as locationService
from Models.MapLocation import MapLocationDropPinModel, MapLocationDropPinUpdateModel

router = APIRouter()


@router.get("/get_wind_speed/", tags=["LOCATION MANAGEMENT"])
def get_wind_speed(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    wind_speed_unit: Literal["kmh", "ms", "mph", "kn"] = "mph",
    timezone: str = "auto",
):
    return locationService.get_wind_speed(
        latitude, longitude, wind_speed_unit, timezone
    )


@router.get("/get_all_country/", tags=["LOCATION MANAGEMENT"])
def get_all_country(request: Request):
    return locationService.get_all_country(request)


@router.get("/get_states_by_country/{country_code}", tags=["LOCATION MANAGEMENT"])
def get_states_by_country(country_code: str):
    return locationService.get_states_by_country(country_code)


@router.get(
    "/get_city_by_country_and_state/{country_code}/{state_code}",
    tags=["LOCATION MANAGEMENT"],
)
def get_city_by_country_and_state(country_code: str, state_code: str):
    return locationService.get_city_by_country_and_state(country_code, state_code)


@router.post("/map-locations/", tags=["SAVE SPOT MANAGEMENT"])
def create_map_location(map_location: MapLocationDropPinModel = Body(...)):
    return locationService.create_map_location(map_location)


@router.get("/map-locations/{page}", tags=["SAVE SPOT MANAGEMENT"])
def get_map_locations(
    page: int,
    limit: int = 10,
    status: Optional[int] = None,
    search_query: Optional[str] = None,
    user_id: Optional[str] = None,
):
    return locationService.get_map_locations(page, limit, status, search_query, user_id)


@router.get("/map-location/{map_location_id}", tags=["SAVE SPOT MANAGEMENT"])
def get_map_location(map_location_id: str, user_id: Optional[str] = None):
    return locationService.get_map_location_by_id(map_location_id, user_id)


@router.put("/map-location/{map_location_id}", tags=["SAVE SPOT MANAGEMENT"])
def update_map_location(
    map_location_id: str,
    map_location: MapLocationDropPinUpdateModel = Body(...),
    user_id: str = Query(..., min_length=1, pattern=r"\S"),
):
    return locationService.update_map_location(map_location_id, map_location, user_id)


@router.delete("/map-location/{map_location_id}", tags=["SAVE SPOT MANAGEMENT"])
def delete_map_location(
    map_location_id: str,
    user_id: str = Query(..., min_length=1, pattern=r"\S"),
):
    return locationService.delete_map_location(map_location_id, user_id)
