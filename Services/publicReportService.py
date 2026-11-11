from datetime import datetime, timezone

from bson import ObjectId

from db import db
from .common import paginate
from .recordUser import user_details_stages

public_report_collection = db["public_report"]


def _active_public_report_filter():
    return {"deleted_at": {"$in": ["", None]}}


def _public_report_projection(base_url):
    return {
        "_id": {"$toString": "$_id"},
        "name": 1,
        "country": 1,
        "state": 1,
        "city": 1,
        "zip_code": 1,
        "latitude": 1,
        "longitude": 1,
        "report_date_time": 1,
        "water_clarity": 1,
        "water_level": 1,
        "temperature": 1,
        "fish_seen": 1,
        "fish_shot": 1,
        "main_species_seen": 1,
        "ramp_condition": 1,
        "images": {
            "$map": {
                "input": {"$ifNull": ["$images", []]},
                "as": "img",
                "in": {"$concat": [base_url + "/", "$$img"]},
            }
        },
        "notes": 1,
        "post_anonymous": 1,
        "status": 1,
        "user_id": 1,
        "created_at": 1,
        "updated_at": 1,
        "updated_by": 1,
    }


def create_public_report(public_report):
    try:
        data = public_report.model_dump()
        result = public_report_collection.insert_one(data)
        data["_id"] = str(result.inserted_id)
        return {
            "message": "Public report created successfully",
            "data": data,
            "status": "success",
        }
    except Exception as exc:
        return {"message": str(exc), "status": "error"}


def get_public_reports(request, page, limit, status=None, search_query=None, user_id=None):
    try:
        base_url = str(request.base_url).rstrip("/")
        if page < 1 or limit < 1:
            return {
                "message": "Page and limit must be greater than zero",
                "status": "error",
            }

        match_stage = _active_public_report_filter()
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
                {"$project": _public_report_projection(base_url)},
                *user_details_stages(),
            ]
        )
        return {
            "data": paginate(public_report_collection, pipeline, page, limit),
            "status": "success",
        }
    except Exception as exc:
        return {"message": str(exc), "status": "error"}


def get_public_report_by_id(request, public_report_id, user_id=None):
    try:
        base_url = str(request.base_url).rstrip("/")
        if not ObjectId.is_valid(public_report_id):
            return {"message": "Invalid public report id", "status": "error"}

        result = list(
            public_report_collection.aggregate(
                [
                    {
                        "$match": {
                            "_id": ObjectId(public_report_id),
                            **_active_public_report_filter(),
                            **({"user_id": user_id} if user_id is not None else {}),
                        }
                    },
                    {"$project": _public_report_projection(base_url)},
                    *user_details_stages(),
                ]
            )
        )
        if not result:
            return {
                "message": "Public report not found",
                "data": None,
                "status": "error",
            }
        return {"data": result[0], "status": "success"}
    except Exception as exc:
        return {"message": str(exc), "status": "error"}


def update_public_report(public_report_id, public_report, user_id):
    try:
        if not isinstance(user_id, str) or not user_id.strip():
            return {"message": "User id is required", "status": "error"}
        if not ObjectId.is_valid(public_report_id):
            return {"message": "Invalid public report id", "status": "error"}

        object_id = ObjectId(public_report_id)
        query = {"_id": object_id, **_active_public_report_filter()}
        data = public_report.model_dump(exclude_unset=True)
        data.pop("user_id", None)
        query["user_id"] = user_id
        if not public_report_collection.find_one(query):
            return {"message": "Public report not found", "status": "error"}

        if not data:
            return {"message": "No fields supplied for update", "status": "error"}
        data["updated_by"] = user_id
        data["updated_at"] = datetime.now(timezone.utc)
        result = public_report_collection.update_one(query, {"$set": data})
        if result.matched_count == 0:
            return {"message": "Public report not found", "status": "error"}
        return {"message": "Public report updated successfully", "status": "success"}
    except Exception as exc:
        return {"message": str(exc), "status": "error"}


def delete_public_report(public_report_id, user_id):
    try:
        if not isinstance(user_id, str) or not user_id.strip():
            return {"message": "User id is required", "status": "error"}
        if not ObjectId.is_valid(public_report_id):
            return {"message": "Invalid public report id", "status": "error"}

        query = {
            "_id": ObjectId(public_report_id),
            **_active_public_report_filter(),
        }
        query["user_id"] = user_id
        data = {
            "deleted_at": datetime.now(timezone.utc),
            "deleted_by": user_id,
        }
        result = public_report_collection.update_one(query, {"$set": data})
        if result.matched_count == 0:
            return {"message": "Public report not found", "status": "error"}
        return {"message": "Public report deleted successfully", "status": "success"}
    except Exception as exc:
        return {"message": str(exc), "status": "error"}
