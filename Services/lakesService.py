from datetime import datetime, timezone

from bson import ObjectId

from db import db
from .common import paginate
from .recordUser import user_details_stages

lake_collection = db["lakes"]


def _active_lake_filter():
    return {"deleted_at": {"$in": ["", None]}}


def _lake_projection():
    return {
        "_id": {"$toString": "$_id"},
        **{field: 1 for field in (
            "name", "country", "state", "city", "zip_code", "latitude",
            "longitude", "water_type", "water_data", "gauge_data", "notes",
            "status", "user_id", "created_at", "updated_at", "updated_by",
        )},
    }


def _validate_water_data(data):
    reference = data.get("water_data")
    if reference is None:
        return None
    if not ObjectId.is_valid(reference):
        return {"message": "Invalid water_data lake id", "status": "error"}
    if not lake_collection.find_one({
        "_id": ObjectId(reference), **_active_lake_filter(),
    }):
        return {"message": "water_data lake not found", "status": "error"}
    return None


def create_lake(lake):
    try:
        data = lake.model_dump()
        error = _validate_water_data(data)
        if error:
            return error
        data.update(
            created_at=datetime.now(timezone.utc), updated_at=None,
            deleted_at=None, deleted_by=None,
        )
        result = lake_collection.insert_one(data)
        data["_id"] = str(result.inserted_id)
        return {
            "message": "Lake created successfully",
            "data": data,
            "status": "success",
        }
    except Exception as exc:
        return {"message": str(exc), "status": "error"}


def get_lakes(page, limit, status=None, search_query=None, user_id=None):
    try:
        if page < 1 or limit < 1:
            return {
                "message": "Page and limit must be greater than zero",
                "status": "error",
            }

        match_stage = _active_lake_filter()
        if user_id is not None:
            match_stage["user_id"] = user_id
        if status is not None:
            match_stage["status"] = status

        if search_query:
            searchable_fields = (
                "name",
                "water_type",
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
                {"$project": _lake_projection()},
                *user_details_stages(),
            ]
        )
        return {
            "data": paginate(lake_collection, pipeline, page, limit),
            "status": "success",
        }
    except Exception as exc:
        return {"message": str(exc), "status": "error"}


def get_lake_by_id(lake_id, user_id=None):
    try:
        if not ObjectId.is_valid(lake_id):
            return {"message": "Invalid lake id", "status": "error"}

        result = list(
            lake_collection.aggregate(
                [
                    {
                        "$match": {
                            "_id": ObjectId(lake_id),
                            **_active_lake_filter(),
                            **({"user_id": user_id} if user_id is not None else {}),
                        }
                    },
                    {"$project": _lake_projection()},
                    *user_details_stages(),
                ]
            )
        )
        if not result:
            return {
                "message": "Lake not found",
                "data": None,
                "status": "error",
            }
        return {"data": result[0], "status": "success"}
    except Exception as exc:
        return {"message": str(exc), "status": "error"}


def update_lake(lake_id, lake, user_id):
    try:
        if not isinstance(user_id, str) or not user_id.strip():
            return {"message": "User id is required", "status": "error"}
        if not ObjectId.is_valid(lake_id):
            return {"message": "Invalid lake id", "status": "error"}

        object_id = ObjectId(lake_id)
        query = {"_id": object_id, **_active_lake_filter()}
        data = lake.model_dump(exclude_unset=True)
        data.pop("user_id", None)
        query["user_id"] = user_id
        if not lake_collection.find_one(query):
            return {"message": "Lake not found", "status": "error"}

        if not data:
            return {"message": "No fields supplied for update", "status": "error"}
        error = _validate_water_data(data)
        if error:
            return error
        data["updated_by"] = user_id
        data["updated_at"] = datetime.now(timezone.utc)
        result = lake_collection.update_one(query, {"$set": data})
        if result.matched_count == 0:
            return {"message": "Lake not found", "status": "error"}
        return {"message": "Lake updated successfully", "status": "success"}
    except Exception as exc:
        return {"message": str(exc), "status": "error"}


def delete_lake(lake_id, user_id):
    try:
        if not isinstance(user_id, str) or not user_id.strip():
            return {"message": "User id is required", "status": "error"}
        if not ObjectId.is_valid(lake_id):
            return {"message": "Invalid lake id", "status": "error"}

        query = {
            "_id": ObjectId(lake_id),
            **_active_lake_filter(),
        }
        query["user_id"] = user_id
        data = {
            "deleted_at": datetime.now(timezone.utc),
            "deleted_by": user_id,
        }
        result = lake_collection.update_one(query, {"$set": data})
        if result.matched_count == 0:
            return {"message": "Lake not found", "status": "error"}
        return {"message": "Lake deleted successfully", "status": "success"}
    except Exception as exc:
        return {"message": str(exc), "status": "error"}
