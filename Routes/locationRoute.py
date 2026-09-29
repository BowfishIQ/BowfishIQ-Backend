from typing import Optional

from fastapi import APIRouter, Body, Request

import Services.locationService as locationService
from Models.MapLocation import MapLocationModel, MapLocationUpdateModel

router = APIRouter()


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


@router.post("/map-locations/", tags=["MAP LOCATION MANAGEMENT"])
def create_map_location(map_location: MapLocationModel = Body(...)):
    return locationService.create_map_location(map_location)


@router.get("/map-locations/{page}", tags=["MAP LOCATION MANAGEMENT"])
def get_map_locations(
    page: int,
    limit: int = 10,
    status: Optional[int] = None,
    search_query: Optional[str] = None,
):
    return locationService.get_map_locations(page, limit, status, search_query)


@router.get("/map-location/{map_location_id}", tags=["MAP LOCATION MANAGEMENT"])
def get_map_location(map_location_id: str):
    return locationService.get_map_location_by_id(map_location_id)


@router.put("/map-location/{map_location_id}", tags=["MAP LOCATION MANAGEMENT"])
def update_map_location(
    map_location_id: str,
    map_location: MapLocationUpdateModel = Body(...),
):
    return locationService.update_map_location(map_location_id, map_location)


@router.delete("/map-location/{map_location_id}", tags=["MAP LOCATION MANAGEMENT"])
def delete_map_location(
    map_location_id: str,
    deleted_by: Optional[str] = None,
):
    return locationService.delete_map_location(map_location_id, deleted_by)
