from datetime import datetime, timezone

import requests
from bson import ObjectId

from db import db
from .common import paginate

collection = db["location"]
map_location_collection = db["map_location"]


def get_wind_speed(latitude, longitude, wind_speed_unit="mph", timezone="auto"):
    try:
        response = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": latitude,
                "longitude": longitude,
                "current": "wind_speed_10m,wind_direction_10m",
                "wind_speed_unit": wind_speed_unit,
                "timezone": timezone,
            },
            timeout=10,
        )
        response.raise_for_status()
        weather = response.json()
        current = weather["current"]
        speed = current["wind_speed_10m"]
        if speed is None:
            return {"message": "Wind speed is unavailable", "status": "error"}
        direction_degrees = current.get("wind_direction_10m")
        compass_directions = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")
        direction = (
            compass_directions[int((direction_degrees % 360 + 22.5) // 45) % 8]
            if direction_degrees is not None
            else None
        )
        return {
            "data": {
                "latitude": latitude,
                "longitude": longitude,
                "wind_speed": speed,
                "wind_speed_unit": weather["current_units"]["wind_speed_10m"],
                "wind_direction": direction,
                "time": current.get("time"),
                "timezone": weather.get("timezone"),
            },
            "status": "success",
        }
    except requests.Timeout:
        return {"message": "Weather service request timed out", "status": "error"}
    except requests.RequestException:
        return {"message": "Unable to fetch wind speed", "status": "error"}
    except (ValueError, KeyError, TypeError):
        return {"message": "Invalid weather service response", "status": "error"}


def _active_map_location_filter():
    return {"deleted_at": {"$in": ["", None]}}


def _map_location_projection():
    return {
        "_id": {"$toString": "$_id"},
        "name": 1,
        "country": 1,
        "state": 1,
        "city": 1,
        "zip_code": 1,
        "latitude": 1,
        "longitude": 1,
        "pin_type": 1,
        "water_body_id": 1,
        "target_species": 1,
        "water_depth_ft": 1,
        "privacy": 1,
        "notes": 1,
        "is_favorite": {"$ifNull": ["$is_favorite", False]},
        "status": 1,
        "created_at": 1,
        "created_date": 1,
        "created_time": 1,
        "created_by": 1,
        "updated_at": 1,
        "updated_by": 1,
    }


def create_map_location(map_location):
    try:
        data = map_location.model_dump()
        result = map_location_collection.insert_one(data)
        data["_id"] = str(result.inserted_id)
        return {
            "message": "Map location created successfully",
            "data": data,
            "status": "success",
        }
    except Exception as exc:
        return {"message": str(exc), "status": "error"}


def get_map_locations(page, limit, status=None, search_query=None):
    try:
        if page < 1 or limit < 1:
            return {
                "message": "Page and limit must be greater than zero",
                "status": "error",
            }

        match_stage = _active_map_location_filter()
        if status is not None:
            match_stage["status"] = status

        if search_query:
            searchable_fields = ("name", "country", "state", "city", "zip_code")
            conditions = [
                {field: {"$regex": search_query, "$options": "i"}}
                for field in searchable_fields
            ]
            if ObjectId.is_valid(search_query):
                conditions.append({"_id": ObjectId(search_query)})
            match_stage["$or"] = conditions

        pipeline = [{"$match": match_stage}]
        pipeline.extend(
            [
                {"$sort": {"created_at": -1}},
                {"$project": _map_location_projection()},
            ]
        )
        return {
            "data": paginate(map_location_collection, pipeline, page, limit),
            "status": "success",
        }
    except Exception as exc:
        return {"message": str(exc), "status": "error"}


def get_map_location_by_id(map_location_id):
    try:
        if not ObjectId.is_valid(map_location_id):
            return {"message": "Invalid map location id", "status": "error"}

        result = list(
            map_location_collection.aggregate(
                [
                    {
                        "$match": {
                            "_id": ObjectId(map_location_id),
                            **_active_map_location_filter(),
                        }
                    },
                    {"$project": _map_location_projection()},
                ]
            )
        )
        if not result:
            return {
                "message": "Map location not found",
                "data": None,
                "status": "error",
            }
        return {"data": result[0], "status": "success"}
    except Exception as exc:
        return {"message": str(exc), "status": "error"}


def update_map_location(map_location_id, map_location):
    try:
        if not ObjectId.is_valid(map_location_id):
            return {"message": "Invalid map location id", "status": "error"}

        object_id = ObjectId(map_location_id)
        query = {"_id": object_id, **_active_map_location_filter()}
        if not map_location_collection.find_one(query):
            return {"message": "Map location not found", "status": "error"}

        data = map_location.model_dump(exclude_unset=True)
        if not data:
            return {"message": "No fields supplied for update", "status": "error"}
        data["updated_at"] = datetime.now(timezone.utc)
        map_location_collection.update_one(query, {"$set": data})
        return {"message": "Map location updated successfully", "status": "success"}
    except Exception as exc:
        return {"message": str(exc), "status": "error"}


def delete_map_location(map_location_id, deleted_by=None):
    try:
        if not ObjectId.is_valid(map_location_id):
            return {"message": "Invalid map location id", "status": "error"}

        query = {
            "_id": ObjectId(map_location_id),
            **_active_map_location_filter(),
        }
        data = {
            "deleted_at": datetime.now(timezone.utc),
            "deleted_by": deleted_by,
        }
        result = map_location_collection.update_one(query, {"$set": data})
        if result.matched_count == 0:
            return {"message": "Map location not found", "status": "error"}
        return {"message": "Map location deleted successfully", "status": "success"}
    except Exception as exc:
        return {"message": str(exc), "status": "error"}


def get_all_country(request):
    try:
        result = collection.find(
            {"deleted_at": None},
            {"currency": 1, "iso2": 1, "name": 1, "id": 1, "_id": 1},
        )
        data = []
        for doc in result:
            doc["_id"] = str(doc["_id"])
            data.append(doc)
        return {"data": data, "status": "success"}
    except Exception as e:
        return {"message": str(e), "status": "error"}


def get_states_by_country(country_code):
    try:
        pipeline = [
            {"$match": {"id": int(country_code)}},
            {"$unwind": "$states"},
            {
                "$project": {
                    "_id": 0,
                    "id": "$states.id",
                    "name": "$states.name",
                    "state_code": "$states.state_code",
                }
            },
        ]
        result = list(db.location.aggregate(pipeline))
        return {"data": result, "status": "success"}
    except Exception as e:
        return {"message": str(e), "status": "error"}


def get_city_by_country_and_state(country_code: int, state_code: int):
    try:
        pipeline = [
            {"$match": {"id": int(country_code)}},
            {"$unwind": "$states"},
            {"$match": {"states.id": int(state_code)}},
            {"$unwind": "$states.cities"},
            {
                "$project": {
                    "_id": 0,
                    "id": "$states.cities.id",
                    "name": "$states.cities.name",
                }
            },
        ]
        result = list(db.location.aggregate(pipeline))
        return {"data": result, "status": "success"}
    except Exception as e:
        return {"message": str(e), "status": "error"}


def get_country_by_id(country_code: int):
    try:
        result = collection.find(
            {"deleted_at": None, "id": country_code},
            {"name": 1, "id": 1, "_id": 1, "iso2": 1},
        )
        data = []
        for doc in result:
            doc["_id"] = str(doc["_id"])
            data.append(doc)
        return {"data": data, "status": "success"}
    except Exception as e:
        return {"message": str(e), "status": "error"}


def get_states_by_state_code_and_country_code(country_code: int, state_code: int):
    try:
        pipeline = [
            {"$match": {"id": country_code}},
            {"$unwind": "$states"},
            {"$match": {"states.id": state_code}},
            {
                "$project": {
                    "_id": 0,
                    "id": "$states.id",
                    "name": "$states.name",
                    "state_code": "$states.state_code",
                }
            },
        ]
        result = list(db.location.aggregate(pipeline))
        return {"data": result, "status": "success"}
    except Exception as e:
        return {"message": str(e), "status": "error"}


def get_city_by_city_id_country_code_and_state_code(country_code, state_code, city_id):
    try:
        pipeline = [
            {"$match": {"id": country_code}},
            {"$unwind": "$states"},
            {"$match": {"states.id": state_code}},
            {"$unwind": "$states.cities"},
            {"$match": {"states.cities.id": city_id}},
            {
                "$project": {
                    "_id": 0,
                    "id": "$states.cities.id",
                    "name": "$states.cities.name",
                }
            },
        ]
        result = list(db.location.aggregate(pipeline))
        return {"data": result, "status": "success"}
    except Exception as e:
        return {"message": str(e), "status": "error"}
