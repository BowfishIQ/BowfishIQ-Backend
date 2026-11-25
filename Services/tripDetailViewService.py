"""Display-only trip details. Stored codes and existing API responses stay unchanged."""

from copy import deepcopy
from datetime import datetime

from bson import ObjectId
from fastapi import HTTPException

from Services import tripDetailsService, tripLogbookService, userTripService


# Labels follow Models/TripDetails.py, including its historical 'lunch_ramp' name.
LABELS = {
    "trip_type": {1: "Regular trip", 2: "Scouting trip"},
    "water_type": {1: "Lake / Reservoir", 2: "River / Creek", 3: "Pond / Small Water", 4: "Coastal"},
    "water_salinity": {1: "Freshwater", 2: "Brackish", 3: "Saltwater"},
    "lunch_ramp": {1: "Bucksaw Resort and Marina", 2: "Bucksaw", 3: "Sterett Creek"},
    "water_clarity": {1: "Clear", 2: "Fair", 3: "Stained", 4: "Muddy"},
    "water_movement": {1: "Still", 2: "Light", 3: "Moderate"},
    "wind": {1: "Calm", 2: "Light", 3: "Moderate", 4: "Strong"},
    "wind_direction": dict(enumerate(("N", "NE", "E", "SE", "S", "SW", "W", "NW"), 1)),
    "water_level": {1: "Low", 2: "Normal", 3: "High"},
    "water_base": {1: "Below", 2: "Above"},
    "fish_location": dict(enumerate(("Shoreline", "Mud flats", "Grass", "Bushes", "Riprap",
                                    "Creek channel", "Main lake", "Suspended", "Flooded timber"), 1)),
    "role": {1: "Captain", 2: "Shooter", 3: "Spotter", 4: "Guest", 5: "Other"},
    "status": {0: "Inactive", 1: "Active", 2: "Blocked"},
}


def _label(field, value):
    if value is None or value == "":
        return None
    text = str(value).strip()
    labels = LABELS[field]
    if text.lstrip("-").isdigit():
        return labels.get(int(text), "Unknown")
    # Preserve already textual legacy records; never return an unknown numeric code.
    return next((label for label in labels.values() if label.lower() == text.lower()), text)


def _labels(field, value):
    if value is None:
        return []
    return [_label(field, item) for item in (value if isinstance(value, list) else [value])]


def _entries(entries, role_field=None):
    result = []
    for entry in tripLogbookService._active(entries):
        row = deepcopy(entry)
        row["status"] = _label("status", row.get("status", 1))
        if role_field:
            row[role_field] = _labels("role", row.get(role_field, row.get("posuser_role")))
            row.pop("posuser_role", None)
        result.append(row)
    return result


def _clock(value):
    if not isinstance(value, str):
        return None
    for fmt in ("%H:%M:%S", "%H:%M", "%I:%M %p"):
        try:
            return datetime.strptime(value.strip(), fmt)
        except ValueError:
            pass
    return None


def _trip_time(trip):
    start, end = _clock(trip.get("start_time")), _clock(trip.get("end_time"))
    hours = None
    overnight = False
    if start is not None and end is not None:
        seconds = (end - start).total_seconds()
        overnight = seconds < 0
        hours = (seconds + (86400 if overnight else 0)) / 3600
    return {
        "start_time": trip.get("start_time"), "end_time": trip.get("end_time"),
        "start_time_display": start.strftime("%I:%M %p").lstrip("0") if start else None,
        "end_time_display": end.strftime("%I:%M %p").lstrip("0") if end else None,
        "duration_hours": hours, "ends_next_day": overnight,
    }


def _rate(count, denominator, digits=1):
    return round(count / denominator, digits) if denominator and count is not None else None


def _species(trip):
    species = {}
    for fish in tripLogbookService._active(trip.get("fish_shot_details")):
        key = (str(fish.get("fish_id") or ""), fish.get("name"))
        if key not in species:
            species[key] = {
                "fish_id": key[0] or None, "name": key[1], "family": None, "count": 0,
                "largest_fish_weight_lb": None, "largest_fish_length_inches": None,
            }
        row = species[key]
        row["count"] += tripLogbookService._number(fish.get("count"))
        for source, target in (("largest_fish", "largest_fish_weight_lb"),
                               ("largest_fish_length", "largest_fish_length_inches")):
            if fish.get(source) is not None:
                row[target] = max(row[target] or 0, tripLogbookService._number(fish[source]))
    return list(species.values())


def _shooter_breakdown(team, crew, total, hours):
    rows = []
    named, unknown = 0, 0
    for entry in team:
        count = (tripLogbookService._number(entry["shot_count"])
                 if entry.get("shot_count") is not None else None)
        if count is not None:
            if (entry.get("name") or "").strip():
                named += count
            else:
                unknown += count
        if "Shooter" in entry["role"] or count is not None:
            rows.append({
                "name": entry.get("name"), "roles": entry["role"], "shot_count": count,
                "duration_hours": hours, "duration_source": "Full trip fallback" if hours is not None else None,
                "fish_per_hour": _rate(count, hours),
            })
    if not team:
        rows = [{"user_id": entry.get("user_id"), "name": entry.get("user_name"),
                 "roles": entry["user_role"], "shot_count": None, "duration_hours": hours,
                 "duration_source": "Full trip fallback" if hours is not None else None,
                 "fish_per_hour": None}
                for entry in crew if "Shooter" in entry["user_role"]]
    return {
        "trip_total": total, "named_fish": named, "unknown_fish": unknown,
        "unassigned_fish": max(0, total - named - unknown),
        "over_attributed_fish": max(0, named + unknown - total), "shooters": rows,
    }


def get_trip_details_by_trip_id(trip_id):
    if not ObjectId.is_valid(trip_id):
        raise HTTPException(status_code=422, detail="Invalid trip_id: expected a MongoDB ObjectId")
    records = list(tripDetailsService.collection.aggregate([
        {"$match": {"_id": ObjectId(trip_id), **tripDetailsService._active_trip_filter()}},
        {"$project": tripDetailsService._trip_projection()},
    ]))
    if not records:
        raise HTTPException(status_code=404, detail="Trip details not found")
    trip = deepcopy(records[0])
    references = list(trip.get("lake_locations") or [])
    userTripService._expand_lake_locations([trip])
    locations_by_id = {str(loc["_id"]): loc for loc in trip["lake_locations"]}
    locations = []
    for reference in dict.fromkeys(str(ref) for ref in references):
        loc = locations_by_id.get(reference, {})
        locations.append({
            "location_id": reference, "name": loc.get("name"), "state": loc.get("state"),
            "city": loc.get("city"), "latitude": loc.get("latitude"), "longitude": loc.get("longitude"),
        })
    species = _species(trip)
    total = sum(fish["count"] for fish in species)
    shooters = tripLogbookService._shooters(trip)
    time = _trip_time(trip)
    hours = time["duration_hours"]
    crew = _entries(trip.get("crew_details"), "user_role")
    team = _entries(trip.get("team_details"), "role")
    not_shot = (tripLogbookService._number(trip["fish_see_not_shot_count"])
                if trip.get("fish_see_not_shot_count") is not None else None)
    data = {
        "trip_id": str(trip["_id"]), "user_id": trip.get("user_id"), "date": trip.get("date"),
        **{field: _label(field, trip.get(field)) for field in
           ("trip_type", "water_type", "water_salinity", "lunch_ramp", "status")},
        "lake_locations": locations, "area_fished": trip.get("area_fished"),
        "summary": {"total_fish": total, "rating": None, "rating_label": None},
        "fish_observations": {"shot": total, "seen_not_shot": not_shot,
                              "seen": total + not_shot if not_shot is not None else None},
        "trip_time": time,
        "performance": {
            "total_fish": total, "shooter_count": shooters,
            "fish_per_shooter": _rate(total, shooters), "fish_per_hour": _rate(total, hours),
            "fish_per_shooter_per_hour": _rate(total, shooters * hours if hours is not None else None, 2),
        },
        "species_breakdown": species,
        "conditions": {
            **{field: _label(field, trip.get(field)) for field in
               ("water_level", "water_base", "water_clarity", "water_movement", "wind", "wind_direction")},
            "water_temp_f": trip.get("water_temp"), "water_depth_ft": trip.get("water_depth"),
            "wind_speed_mph": trip.get("wind_speed"),
            "weather": None, "pressure": None, "moon": None, "moonrise": None, "moonset": None,
        },
        "crew_details": crew, "team_details": team,
        "weighed_fish": {
            "individual_measurements": [], "attribution_available": False,
            # A species maximum is not an individual fish or a shooter assignment.
            "species_maxima": [
                {key: fish[key] for key in ("fish_id", "name", "largest_fish_weight_lb", "largest_fish_length_inches")}
                for fish in species if fish["largest_fish_weight_lb"] is not None
                or fish["largest_fish_length_inches"] is not None
            ],
        },
        "shooter_breakdown": _shooter_breakdown(team, crew, total, hours),
        "fish_location": _labels("fish_location", trip.get("fish_location")),
        "trip_outcome": trip.get("trip_outcome"), "trip_lessons": trip.get("trip_lessons"),
        "trip_notes": trip.get("trip_notes"), "images": trip.get("images") or [],
    }
    return {"status": "success", "data": userTripService._json_safe(data)}
