from datetime import datetime, timezone

from bson import ObjectId

from db import db
from .common import paginate
from .recordUser import user_details_stages

boat_ramp_collection = db["boat_ramp"]


def _active_boat_ramp_filter():
    return {"deleted_at": {"$in": ["", None]}}


def _boat_ramp_projection():
    return {
        "_id": {"$toString": "$_id"},
        "name": 1,
        "lake_river": 1,
        "country": 1,
        "state": 1,
        "city": 1,
        "zip_code": 1,
        "latitude": 1,
        "longitude": 1,
        "ramp_type": 1,
        "parking_type": 1,
        "condition": 1,
        "night_access": 1,
        "fee": 1,
        "dock_availability": 1,
        "bathroom_availability": 1,
        "notes": 1,
        "post_anonymous": 1,
        "status": 1,
        "user_id": 1,
        "created_at": 1,
        "updated_at": 1,
        "updated_by": 1,
    }


def create_boat_ramp(boat_ramp):
    try:
        data = boat_ramp.model_dump()
        result = boat_ramp_collection.insert_one(data)
        data["_id"] = str(result.inserted_id)
        return {
            "message": "Boat ramp created successfully",
            "data": data,
            "status": "success",
        }
    except Exception as exc:
        return {"message": str(exc), "status": "error"}


def get_boat_ramps(page, limit, status=None, search_query=None, user_id=None):
    try:
        if page < 1 or limit < 1:
            return {
                "message": "Page and limit must be greater than zero",
                "status": "error",
            }

        match_stage = _active_boat_ramp_filter()
        if user_id is not None:
            match_stage["user_id"] = user_id
        if status is not None:
            match_stage["status"] = status

        if search_query:
            searchable_fields = (
                "name",
                "lake_river",
                "country",
                "state",
                "city",
                "zip_code",
            )
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
                {"$project": _boat_ramp_projection()},
                *user_details_stages(),
            ]
        )
        return {
            "data": paginate(boat_ramp_collection, pipeline, page, limit),
            "status": "success",
        }
    except Exception as exc:
        return {"message": str(exc), "status": "error"}


def get_boat_ramp_by_id(boat_ramp_id, user_id=None):
    try:
        if not ObjectId.is_valid(boat_ramp_id):
            return {"message": "Invalid boat ramp id", "status": "error"}

        result = list(
            boat_ramp_collection.aggregate(
                [
                    {
                        "$match": {
                            "_id": ObjectId(boat_ramp_id),
                            **_active_boat_ramp_filter(),
                            **({"user_id": user_id} if user_id is not None else {}),
                        }
                    },
                    {"$project": _boat_ramp_projection()},
                    *user_details_stages(),
                ]
            )
        )
        if not result:
            return {
                "message": "Boat ramp not found",
                "data": None,
                "status": "error",
            }
        return {"data": result[0], "status": "success"}
    except Exception as exc:
        return {"message": str(exc), "status": "error"}


def update_boat_ramp(boat_ramp_id, boat_ramp, user_id):
    try:
        if not isinstance(user_id, str) or not user_id.strip():
            return {"message": "User id is required", "status": "error"}
        if not ObjectId.is_valid(boat_ramp_id):
            return {"message": "Invalid boat ramp id", "status": "error"}

        object_id = ObjectId(boat_ramp_id)
        query = {"_id": object_id, **_active_boat_ramp_filter()}
        data = boat_ramp.model_dump(exclude_unset=True)
        data.pop("user_id", None)
        query["user_id"] = user_id
        if not boat_ramp_collection.find_one(query):
            return {"message": "Boat ramp not found", "status": "error"}

        if not data:
            return {"message": "No fields supplied for update", "status": "error"}
        data["updated_by"] = user_id
        data["updated_at"] = datetime.now(timezone.utc)
        result = boat_ramp_collection.update_one(query, {"$set": data})
        if result.matched_count == 0:
            return {"message": "Boat ramp not found", "status": "error"}
        return {"message": "Boat ramp updated successfully", "status": "success"}
    except Exception as exc:
        return {"message": str(exc), "status": "error"}


def delete_boat_ramp(boat_ramp_id, user_id):
    try:
        if not isinstance(user_id, str) or not user_id.strip():
            return {"message": "User id is required", "status": "error"}
        if not ObjectId.is_valid(boat_ramp_id):
            return {"message": "Invalid boat ramp id", "status": "error"}

        query = {
            "_id": ObjectId(boat_ramp_id),
            **_active_boat_ramp_filter(),
        }
        query["user_id"] = user_id
        data = {
            "deleted_at": datetime.now(timezone.utc),
            "deleted_by": user_id,
        }
        result = boat_ramp_collection.update_one(query, {"$set": data})
        if result.matched_count == 0:
            return {"message": "Boat ramp not found", "status": "error"}
        return {"message": "Boat ramp deleted successfully", "status": "success"}
    except Exception as exc:
        return {"message": str(exc), "status": "error"}
