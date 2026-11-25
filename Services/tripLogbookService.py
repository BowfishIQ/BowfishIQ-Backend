"""Read-only logbook reporting, isolated from existing trip endpoints."""

from math import isfinite

from fastapi import HTTPException

from Models.TripDetails import UserTripFilters
from Services import tripDetailsService, userTripService


WATER_TYPES = {"inland": [1, 2, 3], "coastal": [4], "both": [1, 2, 3, 4]}


def _number(value):
    try:
        number = float(value)
        return max(0, number) if isfinite(number) else 0
    except (TypeError, ValueError):
        return 0


def _active(entries):
    return [entry for entry in entries or [] if entry.get("status") in (None, 1)]


def _shooters(trip):
    # Team is the trip's recorded roster; crew is the fallback, not an extra roster.
    team = _active(trip.get("team_details"))
    entries = team or _active(trip.get("crew_details"))
    count = 0
    for entry in entries:
        roles = entry.get("role") if team else entry.get("user_role", entry.get("posuser_role"))
        roles = roles if isinstance(roles, list) else [roles]
        if any(str(role).strip().lower() in ("2", "shooter") for role in roles):
            count += 1
    return count


def get_trip_details_by_user_id_and_category(userid, water_type):
    if water_type not in WATER_TYPES:
        raise HTTPException(status_code=422, detail="water_type must be inland, coastal, or both")
    query = userTripService.build_user_trip_filter(userid, UserTripFilters())
    query["water_type"] = {"$in": WATER_TYPES[water_type]}
    trips = list(tripDetailsService.collection.aggregate([
        {"$match": query},
        {"$set": {"_trip_date": userTripService._trip_date()}},
        {"$sort": {"_trip_date": -1, "created_at": -1, "_id": -1}},
        {"$project": tripDetailsService._trip_projection()},
    ]))
    # Preserve unresolved references so old logs still appear in location history.
    location_refs = [list(trip.get("lake_locations") or []) for trip in trips]
    userTripService._expand_lake_locations(trips)
    cards, history = [], {}
    total_fish, biggest_fish = 0, 0
    counts = {"all": len(trips), "regular": 0, "scouting": 0}
    for trip, references in zip(trips, location_refs):
        fish_counts = {}
        largest = 0
        for fish in _active(trip.get("fish_shot_details")):
            key = (str(fish.get("fish_id") or ""), fish.get("name"))
            fish_counts[key] = fish_counts.get(key, 0) + _number(fish.get("count"))
            largest = max(largest, _number(fish.get("largest_fish")))
        fish = [{"fish_id": key[0] or None, "name": key[1], "count": count}
                for key, count in fish_counts.items()]
        fish_total = sum(row["count"] for row in fish)
        shooters = _shooters(trip)
        locations = [{"location_id": str(loc["_id"]), "name": loc.get("name"),
                      "state": loc.get("state")} for loc in trip["lake_locations"]]
        resolved_ids = {loc["location_id"] for loc in locations}
        locations.extend({"location_id": str(ref), "name": None, "state": None}
                         for ref in references if str(ref) not in resolved_ids)
        # Count a trip only once per location even when references are duplicated.
        locations = list({loc["location_id"]: loc for loc in locations}.values())
        if not locations:
            locations = [{"location_id": None, "name": trip.get("area_fished"), "state": None}]
        trip_id = str(trip["_id"])
        cards.append({
            "trip_id": trip_id, "date": trip.get("date"),
            "trip_type": trip.get("trip_type"), "is_scouting": trip.get("trip_type") == 2,
            "water_type": trip.get("water_type"), "locations": locations,
            "area_fished": trip.get("area_fished"), "fish_counts": fish,
            "total_fish": fish_total, "shooter_count": shooters,
            "fish_per_shooter": round(fish_total / shooters, 1) if shooters else 0,
            "largest_fish_weight_lb": largest, "rating": None,
        })
        total_fish += fish_total
        biggest_fish = max(biggest_fish, largest)
        if trip.get("trip_type") in (1, 2):
            counts["regular" if trip["trip_type"] == 1 else "scouting"] += 1
        for location in locations:
            # Fallback areas remain separate across water types.
            key = (location["location_id"], None) if location["location_id"] else (
                trip.get("water_type"), trip.get("area_fished"))
            if key not in history:
                history[key] = {
                    **location, "last_trip_date": trip.get("date"),
                    "total_trips": 0, "total_fish": 0, "best_night": 0, "trip_ids": [],
                }
            row = history[key]
            row["total_trips"] += 1
            row["total_fish"] += fish_total
            row["best_night"] = max(row["best_night"], fish_total)
            row["trip_ids"].append(trip_id)
    return {"status": "success", "data": {
        "userid": userid, "water_type": water_type, "water_types": WATER_TYPES[water_type],
        "summary": {"lifetime_trips": len(trips), "boat_fish_all_time": total_fish,
                    "biggest_boat_fish_lb": biggest_fish},
        "trip_counts": counts, "trips": cards, "trip_history": list(history.values()),
    }}
