from datetime import datetime

from bson import ObjectId

from db import db
from Models.TripDetails import TripDetailsModel
from .common import paginate

collection = db["trip_details"]


def _active_trip_filter():
    return {"deleted_at": {"$in": ["", None]}}


def _trip_projection():
    return {
        "_id": {"$toString": "$_id"},
        **{field: 1 for field in TripDetailsModel.model_fields},
    }


def create_trip_details(trip_details):
    try:
        data = trip_details.model_dump()
        result = collection.insert_one(data)
        data["_id"] = str(result.inserted_id)
        return {
            "message": "Trip details created successfully",
            "data": data,
            "status": "success",
        }
    except Exception as exc:
        return {"message": str(exc), "status": "error"}


def get_trip_details(page, limit, status=None, search_query=None, user_id=None):
    try:
        if page < 1 or limit < 1:
            return {
                "message": "Page and limit must be greater than zero",
                "status": "error",
            }
        query = _active_trip_filter()
        if status is not None:
            query["status"] = status
        if user_id is not None:
            query["user_id"] = user_id
        if search_query:
            fields = ("area_fished", "lunch_ramp", "date", "trip_outcome",
                      "trip_lessons", "trip_notes")
            conditions = [
                {field: {"$regex": search_query, "$options": "i"}}
                for field in fields
            ]
            if ObjectId.is_valid(search_query):
                conditions.append({"_id": ObjectId(search_query)})
            query["$or"] = conditions
        pipeline = [
            {"$match": query},
            {"$sort": {"created_at": -1}},
            {"$project": _trip_projection()},
        ]
        return {"data": paginate(collection, pipeline, page, limit), "status": "success"}
    except Exception as exc:
        return {"message": str(exc), "status": "error"}


def get_trip_details_by_id(trip_details_id):
    try:
        if not ObjectId.is_valid(trip_details_id):
            return {"message": "Invalid trip details id", "status": "error"}
        result = list(collection.aggregate([
            {"$match": {"_id": ObjectId(trip_details_id), **_active_trip_filter()}},
            {"$project": _trip_projection()},
        ]))
        if not result:
            return {"message": "Trip details not found", "data": None, "status": "error"}
        return {"data": result[0], "status": "success"}
    except Exception as exc:
        return {"message": str(exc), "status": "error"}


def update_trip_details(trip_details_id, trip_details):
    try:
        if not ObjectId.is_valid(trip_details_id):
            return {"message": "Invalid trip details id", "status": "error"}
        data = trip_details.model_dump(exclude_unset=True)
        if not data:
            return {"message": "No fields supplied for update", "status": "error"}
        data["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        query = {"_id": ObjectId(trip_details_id), **_active_trip_filter()}
        result = collection.update_one(query, {"$set": data})
        if result.matched_count == 0:
            return {"message": "Trip details not found", "status": "error"}
        return {"message": "Trip details updated successfully", "status": "success"}
    except Exception as exc:
        return {"message": str(exc), "status": "error"}


def delete_trip_details(trip_details_id, deleted_by=None):
    try:
        if not ObjectId.is_valid(trip_details_id):
            return {"message": "Invalid trip details id", "status": "error"}
        query = {"_id": ObjectId(trip_details_id), **_active_trip_filter()}
        data = {
            "deleted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "deleted_by": deleted_by,
        }
        result = collection.update_one(query, {"$set": data})
        if result.matched_count == 0:
            return {"message": "Trip details not found", "status": "error"}
        return {"message": "Trip details deleted successfully", "status": "success"}
    except Exception as exc:
        return {"message": str(exc), "status": "error"}
