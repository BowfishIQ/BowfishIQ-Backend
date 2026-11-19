from datetime import datetime, timezone
import re

from bson import ObjectId

from db import db
from .common import paginate

coastal_collection = db["coastal"]


def _active_filter():
    return {"deleted_at": {"$in": ["", None]}}


def _projection():
    return {
        "_id": {"$toString": "$_id"},
        **{field: 1 for field in (
            "state", "area", "latitude", "longitude", "status",
            "created_at", "updated_at",
        )},
        "count": {"$size": {"$ifNull": ["$area", []]}},
    }


def create_coastal(coastal):
    try:
        data = coastal.model_dump()
        data.update(
            created_at=datetime.now(timezone.utc), updated_at=None,
            deleted_at=None, deleted_by=None,
        )
        result = coastal_collection.insert_one(data)
        data["_id"] = str(result.inserted_id)
        data["count"] = len(data.get("area") or [])
        return {"message": "Coastal created successfully", "data": data, "status": "success"}
    except Exception as exc:
        return {"message": str(exc), "status": "error"}


def get_coastals(page, limit, status=None, search_query=None, state=None):
    try:
        if page < 1 or limit < 1:
            return {"message": "Page and limit must be greater than zero", "status": "error"}
        query = _active_filter()
        if status is not None:
            query["status"] = status
        if state is not None:
            query["state"] = state
        if search_query:
            query["$or"] = [
                {field: {"$regex": re.escape(search_query), "$options": "i"}}
                for field in ("state", "area.name", "area.water_body", "area.id")
            ]
            if ObjectId.is_valid(search_query):
                query["$or"].append({"_id": ObjectId(search_query)})
        pipeline = [
            {"$match": query}, {"$sort": {"state": 1, "_id": 1}},
            {"$project": _projection()},
        ]
        return {"data": paginate(coastal_collection, pipeline, page, limit), "status": "success"}
    except Exception as exc:
        return {"message": str(exc), "status": "error"}


def get_coastal_by_id(coastal_id):
    try:
        if not ObjectId.is_valid(coastal_id):
            return {"message": "Invalid coastal id", "status": "error"}
        result = list(coastal_collection.aggregate([
            {"$match": {"_id": ObjectId(coastal_id), **_active_filter()}},
            {"$project": _projection()},
        ]))
        if not result:
            return {"message": "Coastal not found", "data": None, "status": "error"}
        return {"data": result[0], "status": "success"}
    except Exception as exc:
        return {"message": str(exc), "status": "error"}


def update_coastal(coastal_id, coastal):
    try:
        if not ObjectId.is_valid(coastal_id):
            return {"message": "Invalid coastal id", "status": "error"}
        data = coastal.model_dump(exclude_unset=True)
        # Deletion metadata is managed only by the delete endpoint.
        for field in ("deleted_at", "deleted_by", "updated_at"):
            data.pop(field, None)
        if not data:
            return {"message": "No fields supplied for update", "status": "error"}
        # Include generated IDs even when the client omitted them in nested areas.
        if coastal.area is not None and "area" in data:
            data["area"] = [area.model_dump() for area in coastal.area]
        data["updated_at"] = datetime.now(timezone.utc)
        result = coastal_collection.update_one(
            {"_id": ObjectId(coastal_id), **_active_filter()}, {"$set": data},
        )
        if result.matched_count == 0:
            return {"message": "Coastal not found", "status": "error"}
        return {"message": "Coastal updated successfully", "status": "success"}
    except Exception as exc:
        return {"message": str(exc), "status": "error"}


def delete_coastal(coastal_id, user_id):
    try:
        if not isinstance(user_id, str) or not user_id.strip():
            return {"message": "User id is required", "status": "error"}
        if not ObjectId.is_valid(coastal_id):
            return {"message": "Invalid coastal id", "status": "error"}
        now = datetime.now(timezone.utc)
        result = coastal_collection.update_one(
            {"_id": ObjectId(coastal_id), **_active_filter()},
            {"$set": {"deleted_at": now, "deleted_by": user_id, "updated_at": now}},
        )
        if result.matched_count == 0:
            return {"message": "Coastal not found", "status": "error"}
        return {"message": "Coastal deleted successfully", "status": "success"}
    except Exception as exc:
        return {"message": str(exc), "status": "error"}
