"""User trip reporting. All counting happens in MongoDB before pagination."""

from datetime import datetime

from bson import ObjectId
from fastapi import HTTPException

from Services import locationService, tripDetailsService
from Models.TripDetails import UserTripFilters


ROLE_NAMES = {"1": "captain", "2": "shooter", "3": "spotter", "4": "guest", "5": "other"}
BREAKDOWN_FIELDS = (
    "trip_type", "status", "water_type", "water_salinity", "water_clarity",
    "water_movement", "wind", "wind_direction", "water_level", "water_base",
    "fish_location", "lunch_ramp",
)


def _ids(user_id):
    if not user_id.strip():
        raise HTTPException(status_code=422, detail="User ID cannot be blank")
    # Models store strings; also match legacy BSON ObjectId references.
    return [user_id, ObjectId(user_id)] if ObjectId.is_valid(user_id) else [user_id]


def _parse_date(value, field):
    if value is None:
        return None
    for fmt in ("%d-%m-%Y", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(value, fmt)
            if parsed.strftime(fmt) == value:
                return parsed
        except ValueError:
            pass
    raise HTTPException(status_code=422, detail=f"{field} must be a valid DD-MM-YYYY or YYYY-MM-DD date")


def _trip_date():
    # Dates are stored as DD-MM-YYYY: string comparison gives incorrect ranges.
    return {"$ifNull": [
        {"$dateFromString": {"dateString": "$date", "format": "%d-%m-%Y", "onError": None, "onNull": None}},
        {"$dateFromString": {"dateString": "$date", "format": "%Y-%m-%d", "onError": None, "onNull": None}},
    ]}


def build_user_trip_filter(user_id, filters):
    ids = _ids(user_id)
    exact = _parse_date(filters.date, "date")
    start = _parse_date(filters.start_date, "start_date")
    end = _parse_date(filters.end_date, "end_date")
    if exact and (start or end):
        raise HTTPException(status_code=422, detail="Use date or start_date/end_date, not both")
    if start and end and start > end:
        raise HTTPException(status_code=422, detail="start_date must be on or before end_date")

    query = tripDetailsService._active_trip_filter()
    owner = {"user_id": {"$in": ids}}
    crew = {"crew_details": {"$elemMatch": {
        "user_id": {"$in": ids}, "status": {"$in": [1, None]},
    }}}
    if filters.scope == "owner":
        query.update(owner)
    elif filters.scope == "crew":
        query.update(crew)
    else:
        query["$or"] = [owner, crew]
    if filters.trip_id is not None:
        if not ObjectId.is_valid(filters.trip_id):
            raise HTTPException(status_code=422, detail="Invalid trip_id: expected a MongoDB ObjectId")
        query["_id"] = ObjectId(filters.trip_id)
    for field in ("trip_type", "status", "water_type", "water_salinity"):
        value = getattr(filters, field)
        if value is not None:
            query[field] = value
    if filters.lake_location_id is not None:
        query["lake_locations"] = {"$in": _ids(filters.lake_location_id)}
    comparisons = []
    if exact:
        comparisons.append({"$eq": [_trip_date(), exact]})
    if start:
        comparisons.append({"$gte": [_trip_date(), start]})
    if end:
        comparisons.append({"$lte": [_trip_date(), end]})
    if comparisons:
        # Explicitly exclude missing/invalid dates, including in end-only queries.
        query["$expr"] = {"$and": [{"$ne": [_trip_date(), None]}, *comparisons]}
    return query


def _json_safe(value):
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def _expand_lake_locations(trips):
    """Resolve a page's references in one query, preserving each trip's order."""
    location_ids = {
        ObjectId(location_id)
        for trip in trips
        for location_id in (trip.get("lake_locations") or [])
        if isinstance(location_id, (str, ObjectId)) and ObjectId.is_valid(location_id)
    }
    locations = {}
    if location_ids:
        records = locationService.map_location_collection.aggregate([
            {"$match": {
                "_id": {"$in": list(location_ids)},
                **locationService._active_map_location_filter(),
            }},
            {"$project": locationService._map_location_projection()},
        ])
        locations = {str(record["_id"]): record for record in records}
    for trip in trips:
        trip["lake_locations"] = [
            locations[str(ObjectId(location_id))]
            for location_id in (trip.get("lake_locations") or [])
            if isinstance(location_id, (str, ObjectId))
            and ObjectId.is_valid(location_id)
            and str(ObjectId(location_id)) in locations
        ]
    return trips


def get_user_trip_details(user_id, filters: UserTripFilters, page=1, limit=10, sort_order="desc"):
    query = build_user_trip_filter(user_id, filters)
    direction = 1 if sort_order == "asc" else -1
    # Match before $facet so unrelated trips do not enter the pagination stage.
    pipeline = [
        {"$match": query},
        {"$facet": {
            "data": [
                {"$set": {"_trip_date": _trip_date()}},
                {"$sort": {"_trip_date": direction, "created_at": direction, "_id": direction}},
                {"$skip": (page - 1) * limit}, {"$limit": limit},
                {"$project": tripDetailsService._trip_projection()},
            ],
            "total": [{"$count": "count"}],
        }},
    ]
    result = next(iter(tripDetailsService.collection.aggregate(pipeline)), {})
    total = result.get("total", [{}])[0].get("count", 0) if result.get("total") else 0
    return {"status": "success", "data": {
        "page": page, "limit": limit, "total": total,
        "totalPages": (total + limit - 1) // limit,
        "data": _json_safe(_expand_lake_locations(result.get("data", []))),
        "start_count": (page - 1) * limit,
        "end_count": min(page * limit, total),
    }}


def _active_entries(field):
    return {"$filter": {
        "input": {"$ifNull": [f"${field}", []]}, "as": "entry",
        "cond": {"$in": [{"$ifNull": ["$$entry.status", 1]}, [1]]},
    }}


def _number(value):
    return {"$convert": {"input": value, "to": "double", "onError": 0, "onNull": 0}}


def _array_total(array, field):
    return {"$sum": {"$map": {"input": array, "as": "entry", "in": _number(f"$$entry.{field}")}}}


def _role(value):
    normalized = {"$toLower": {"$trim": {"input": {
        "$convert": {"input": value, "to": "string", "onError": "", "onNull": ""},
    }}}}
    return {"$switch": {
        "branches": [{"case": {"$in": [normalized, [code, name]]}, "then": name}
                     for code, name in ROLE_NAMES.items()],
        "default": "other",
    }}


def _as_array(value):
    """Support current multi-select values and older scalar records."""
    return {"$cond": [{"$isArray": value}, value, [value]]}


def _role_facet(array, role_field, unique_trips=False, legacy_field=None):
    value = f"${array}.{role_field}"
    if legacy_field:
        value = {"$ifNull": [value, f"${array}.{legacy_field}"]}
    stages = [
        {"$unwind": {"path": f"${array}", "includeArrayIndex": "_role_entry_index"}},
        {"$set": {"_roles": _as_array(value)}},
        {"$unwind": {"path": "$_roles", "preserveNullAndEmptyArrays": True}},
        {"$set": {"_role": _role("$_roles")}},
        # Normalize and deduplicate roles on each entry before counting.
        {"$group": {"_id": {"trip": "$_id", "entry": "$_role_entry_index", "role": "$_role"}}},
    ]
    if unique_trips:
        stages.append({"$group": {"_id": {"trip": "$_id.trip", "role": "$_id.role"}}})
    stages.append({"$group": {
        "_id": "$_id.role", "count": {"$sum": 1},
    }})
    return stages


def get_user_trip_summary(user_id, filters: UserTripFilters):
    query = build_user_trip_filter(user_id, filters)
    ids = _ids(user_id)
    group = {
        "_id": None,
        "total_trips": {"$sum": 1},
        "owned_trips": {"$sum": {"$cond": [{"$in": ["$user_id", ids]}, 1, 0]}},
        "crew_trips": {"$sum": {"$cond": [{"$gt": [{"$size": "$_user_crew"}, 0]}, 1, 0]}},
        "regular_trips": {"$sum": {"$cond": [{"$eq": ["$trip_type", 1]}, 1, 0]}},
        "scouting_trips": {"$sum": {"$cond": [{"$eq": ["$trip_type", 2]}, 1, 0]}},
        "total_fish_caught": {"$sum": _array_total("$_fish", "count")},
        "total_fish_seen_not_shot": {"$sum": _number("$fish_see_not_shot_count")},
        "total_team_shots": {"$sum": _array_total("$_team", "shot_count")},
        "total_crew_entries": {"$sum": {"$size": "$_crew"}},
        "total_team_entries": {"$sum": {"$size": "$_team"}},
        "total_images": {"$sum": {"$size": {"$ifNull": ["$images", []]}}},
        "largest_fish_weight_lb": {"$max": {"$max": {"$map": {
            "input": "$_fish", "as": "fish", "in": _number("$$fish.largest_fish"),
        }}}},
        "largest_fish_length_inches": {"$max": {"$max": {"$map": {
            "input": "$_fish", "as": "fish", "in": _number("$$fish.largest_fish_length"),
        }}}},
    }
    facets = {
        "totals": [{"$group": group}],
        "user_role_counts": _role_facet("_user_crew", "user_role", unique_trips=True, legacy_field="posuser_role"),
        "team_role_counts": _role_facet("_team", "role"),
        "fish_counts": [
            {"$unwind": "$_fish"},
            {"$group": {
                "_id": {"fish_id": "$_fish.fish_id", "name": "$_fish.name"},
                "count": {"$sum": _number("$_fish.count")},
            }},
            {"$sort": {"count": -1, "_id.fish_id": 1, "_id.name": 1}},
        ],
    }
    for field in BREAKDOWN_FIELDS:
        stages = []
        if field == "fish_location":
            stages = [
                {"$set": {"fish_location": {"$setUnion": [_as_array("$fish_location"), []]}}},
                {"$unwind": {"path": "$fish_location", "preserveNullAndEmptyArrays": True}},
            ]
        facets[field] = stages + [
            {"$group": {"_id": {"$ifNull": [f"${field}", None]}, "count": {"$sum": 1}}},
            {"$sort": {"_id": 1}},
        ]
    pipeline = [
        {"$match": query},
        {"$set": {"_fish": _active_entries("fish_shot_details"),
                   "_team": _active_entries("team_details"), "_crew": _active_entries("crew_details")}},
        {"$set": {"_user_crew": {"$filter": {
            "input": "$_crew", "as": "crew", "cond": {"$in": ["$$crew.user_id", ids]},
        }}}},
        {"$facet": facets},
    ]
    result = next(iter(tripDetailsService.collection.aggregate(pipeline)), {})
    totals = result.get("totals", [{}])[0] if result.get("totals") else {}
    data = {key: totals.get(key) or 0 for key in group if key != "_id"}
    for field in ("user_role_counts", "team_role_counts"):
        data[field] = {name: 0 for name in ROLE_NAMES.values()}
        data[field].update({row["_id"]: row["count"] for row in result.get(field, [])})
    data["fish_counts"] = [{**row["_id"], "count": row["count"]} for row in result.get("fish_counts", [])]
    data["breakdowns"] = {field: [{"value": row["_id"], "count": row["count"]}
                                    for row in result.get(field, [])] for field in BREAKDOWN_FIELDS}
    return {"status": "success", "data": _json_safe(data)}
