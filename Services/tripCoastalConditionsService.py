"""NOAA/NWS coastal snapshots, isolated from trip records and existing endpoints.

Provider specifications:
https://api.tidesandcurrents.noaa.gov/api/prod/
https://api.tidesandcurrents.noaa.gov/api/prod/responseHelp.html
https://api.tidesandcurrents.noaa.gov/mdapi/prod/
https://www.weather.gov/documentation/services-web-api
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from math import asin, cos, isfinite, radians, sin, sqrt
from urllib.parse import urlparse

import requests
from bson import ObjectId
from fastapi import HTTPException
from pymongo.errors import PyMongoError

from config import NWS_USER_AGENT
from db import db
from Services import tripDetailsService, userTripService


collection = db["trip_coastal_conditions"]
NOAA_DATA = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
NOAA_STATIONS = "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations.json"
NWS = "https://api.weather.gov"
MAX_STATION_KM = 50
UTC = timezone.utc


class ProviderUnavailable(Exception):
    pass


def _now():
    return datetime.now(UTC)


def _number(value):
    try:
        number = float(value)
        return number if isfinite(number) else None
    except (ValueError, TypeError):
        return None


def _timestamp(value):
    if not isinstance(value, str):
        return None
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return result.replace(tzinfo=UTC) if result.tzinfo is None else result.astimezone(UTC)
    except ValueError:
        return None


def _json(url, params=None):
    # Only fixed NOAA URLs and validated NWS links are requested.
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc not in ("api.weather.gov", "api.tidesandcurrents.noaa.gov"):
        raise ProviderUnavailable("Untrusted provider URL")
    try:
        response = requests.get(url, params=params, headers={
            "User-Agent": NWS_USER_AGENT, "Accept": "application/geo+json" if parsed.netloc == "api.weather.gov" else "application/json",
        }, timeout=(5, 15), allow_redirects=False)
        response.raise_for_status()
        if response.status_code != 200:
            raise ProviderUnavailable("Provider returned a non-success response")
        data = response.json()
        if not isinstance(data, dict) or data.get("error"):
            raise ProviderUnavailable("Provider has no usable data for this request")
        return data
    except (requests.RequestException, ValueError):
        raise ProviderUnavailable("Provider request failed") from None


def _distance(lat, lon, other_lat, other_lon):
    dlat, dlon = radians(other_lat - lat), radians(other_lon - lon)
    a = sin(dlat / 2) ** 2 + cos(radians(lat)) * cos(radians(other_lat)) * sin(dlon / 2) ** 2
    return 6371 * 2 * asin(min(1, sqrt(a)))


@lru_cache(maxsize=32)
def _station_list(kind, hour_bucket):
    # Cache station metadata, not observations. The bucket expires after one hour.
    data = _json(NOAA_STATIONS, {"type": kind})
    stations = data.get("stations", data.get("stationList"))
    if not isinstance(stations, list):
        raise ProviderUnavailable("Station metadata is unavailable")
    return stations


def _nearest(kind, location, now):
    candidates = []
    for station in _station_list(kind, int(now.timestamp()) // 3600):
        if not str(station.get("id", "")).isdigit():
            continue
        lat, lon = _number(station.get("lat")), _number(station.get("lng"))
        if lat is None or lon is None or not (-90 <= lat <= 90 and -180 <= lon <= 180):
            continue
        if station.get("greatlakes") or station.get("tidal") is False:
            continue
        distance = _distance(location["latitude"], location["longitude"], lat, lon)
        if distance <= MAX_STATION_KM:
            candidates.append((distance, str(station.get("id", "")), station))
    if not candidates:
        raise ProviderUnavailable("No suitable station within 50 km")
    distance, station_id, station = min(candidates, key=lambda row: (row[0], row[1]))
    return {"id": station_id, "name": station.get("name"), "latitude": float(station["lat"]),
            "longitude": float(station["lng"]), "distance_km": round(distance, 3)}


def _noaa(product, kind, location, now):
    station = _nearest(kind, location, now)
    params = {"station": station["id"], "product": product, "units": "english",
              "time_zone": "gmt", "format": "json", "application": "BowfishIQ"}
    if product == "predictions":
        params.update(begin_date=now.strftime("%Y%m%d %H:%M"),
                      end_date=(now + timedelta(hours=48)).strftime("%Y%m%d %H:%M"),
                      interval="hilo", datum="MLLW")
    else:
        params.update(begin_date=(now - timedelta(hours=1)).strftime("%Y%m%d %H:%M"),
                      end_date=now.strftime("%Y%m%d %H:%M"))
        if product == "water_level":
            params["datum"] = "MLLW"
    data = _json(NOAA_DATA, params)
    return data, {"provider": "NOAA CO-OPS", "url": NOAA_DATA, "product": product,
                  "station": station, "time_zone": "UTC"}


def _fresh_rows(rows, now, minutes, water_level=False):
    result = []
    for row in rows:
        timestamp = _timestamp(row.get("t"))
        if timestamp is None or not 0 <= (now - timestamp).total_seconds() <= minutes * 60:
            continue
        flags = str(row.get("f") or "").split(",")
        # The first water-level flag counts outliers; subsequent flags mark failures.
        checked = flags[1:] if water_level else flags
        if any(flag.strip() not in ("", "0") for flag in checked):
            continue
        result.append((timestamp, row))
    return sorted(result, key=lambda item: item[0])


def _observation(product, kind, field, unit, location, now, max_age=60):
    data, source = _noaa(product, kind, location, now)
    rows = [(time, row) for time, row in _fresh_rows(data.get("data", []), now, max_age,
            product == "water_level") if _number(row.get(field)) is not None
            and (product not in ("wind", "salinity") or _number(row[field]) >= 0)]
    if not rows:
        raise ProviderUnavailable("No recent unflagged observation")
    time, row = rows[-1]
    result = {"value": _number(row[field]), "unit": unit, "observed_at": time.isoformat(),
              "source": source, "quality": row.get("q"), "flags": row.get("f")}
    if product == "water_level":
        result["datum"] = "MLLW"
        trend = None
        if len(rows) > 1 and 0 < (time - rows[-2][0]).total_seconds() <= 12 * 60:
            delta = result["value"] - _number(rows[-2][1][field])
            trend = "rising" if delta > 0 else "falling" if delta < 0 else "steady"
        result["trend"] = trend
        result["trend_basis"] = "Change between consecutive station water-level observations; not tidal current"
    if product == "wind":
        # NOAA english wind values are knots, not mph.
        result["value"] *= 1.150779448
        result["direction_degrees"] = _number(row.get("d"))
        result["direction"] = row.get("dr")
        result["gust_mph"] = (_number(row.get("g")) * 1.150779448
                              if _number(row.get("g")) is not None else None)
    return result


def _predictions(location, now):
    data, source = _noaa("predictions", "tidepredictions", location, now)
    result = {"next_high": None, "next_low": None}
    rows = sorted(((_timestamp(row.get("t")), row) for row in data.get("predictions", [])
                   if _timestamp(row.get("t")) is not None), key=lambda item: item[0])
    for time, row in rows:
        if time <= now or _number(row.get("v")) is None or row.get("type") not in ("H", "L"):
            continue
        key = "next_high" if row["type"] == "H" else "next_low"
        if result[key] is None:
            result[key] = {"at": time.isoformat(), "height_ft": _number(row["v"]), "datum": "MLLW",
                           "kind": "prediction", "source": source}
    if not any(result.values()):
        raise ProviderUnavailable("No high/low predictions available in the next 48 hours")
    return result


def _alerts(location, now):
    data = _json(f"{NWS}/alerts/active", {"point": f'{location["latitude"]},{location["longitude"]}'})
    if not isinstance(data.get("features"), list):
        raise ProviderUnavailable("Alerts response is incomplete")
    alerts = []
    for feature in data["features"]:
        row = feature.get("properties") or {}
        expires = _timestamp(row.get("ends")) or _timestamp(row.get("expires"))
        effective = _timestamp(row.get("effective"))
        if (expires is not None and expires <= now) or (effective is not None and effective > now):
            continue
        alerts.append({key: row.get(key) for key in (
            "id", "event", "headline", "severity", "effective", "onset", "ends", "expires", "description", "instruction")})
    return {"items": alerts, "small_craft_advisory": any(
        row["event"] == "Small Craft Advisory" for row in alerts), "checked_at": now.isoformat(),
        "source": {"provider": "NWS", "url": f"{NWS}/alerts/active"}}


def _nws_wind(location, now):
    point = _json(f'{NWS}/points/{location["latitude"]:.4f},{location["longitude"]:.4f}')
    url = (point.get("properties") or {}).get("observationStations")
    if not isinstance(url, str):
        raise ProviderUnavailable("NWS observation stations unavailable for this coastal point")
    stations = _json(url)
    candidates = []
    for station in stations.get("features", []):
        coords = (station.get("geometry") or {}).get("coordinates") or []
        if len(coords) < 2 or _number(coords[0]) is None or _number(coords[1]) is None:
            continue
        if not (-180 <= float(coords[0]) <= 180 and -90 <= float(coords[1]) <= 90):
            continue
        distance = _distance(location["latitude"], location["longitude"], float(coords[1]), float(coords[0]))
        station_id = (station.get("properties") or {}).get("stationIdentifier")
        if distance <= MAX_STATION_KM and isinstance(station_id, str) and station_id.isalnum():
            candidates.append((distance, station_id))
    for distance, station_id in sorted(candidates)[:3]:
        url = f"{NWS}/stations/{station_id}/observations/latest"
        try:
            props = _json(url).get("properties") or {}
        except ProviderUnavailable:
            continue
        time = _timestamp(props.get("timestamp"))
        speed = props.get("windSpeed") or {}
        value = _number(speed.get("value"))
        factor = {"wmoUnit:km_h-1": 0.621371192, "wmoUnit:m_s-1": 2.236936292,
                  "wmoUnit:kn": 1.150779448, "wmoUnit:mi_h-1": 1}.get(speed.get("unitCode"))
        if (time is None or not 0 <= (now - time).total_seconds() <= 3600 or value is None
                or value < 0 or factor is None or speed.get("qualityControl") not in (None, "V", "S")):
            continue
        return {"value": value * factor, "unit": "mph", "observed_at": time.isoformat(),
                "direction_degrees": _number((props.get("windDirection") or {}).get("value")),
                "direction": None, "gust_mph": None,
                "quality": speed.get("qualityControl"),
                "source": {"provider": "NWS", "url": url, "station": {"id": station_id,
                           "distance_km": round(distance, 3)}}}
    raise ProviderUnavailable("No recent supported NWS wind observation within 50 km")


def _snapshot(location):
    now = _now()
    readings, unavailable = {}, {}
    tasks = {
        "water_level": lambda: _observation("water_level", "waterlevels", "v", "ft", location, now, 30),
        "water_temperature": lambda: _observation("water_temperature", "watertemp", "v", "degF", location, now),
        "wind": lambda: _observation("wind", "met", "s", "mph", location, now),
        "salinity": lambda: _observation("salinity", "cond", "s", "PSU", location, now),
        "tides": lambda: _predictions(location, now), "alerts": lambda: _alerts(location, now),
    }
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {name: pool.submit(task) for name, task in tasks.items()}
        for name, future in futures.items():
            try:
                readings[name] = future.result()
            except (ProviderUnavailable, KeyError, TypeError, ValueError):
                readings[name] = None
                unavailable[name] = "No recent usable provider data within the station coverage limit, or provider unavailable."
    if readings["wind"] is None:
        try:
            readings["wind"] = _nws_wind(location, now)
            unavailable.pop("wind", None)
        except (ProviderUnavailable, KeyError, TypeError, ValueError):
            pass
    if not any(value is not None for value in readings.values()):
        raise HTTPException(503, "No usable coastal conditions available; existing snapshots were preserved")
    readings["waves"] = None
    unavailable["waves"] = "Observed wave height is not provided by the requested CO-OPS products or NWS station observation fields."
    return {"captured_at": now.isoformat(), "capture_basis": "Current observations at button press, not historical trip times",
            "location": location, "readings": readings, "availability": "partial" if unavailable else "complete",
            "unavailable": unavailable, "time_zone": "UTC", "station_limit_km": MAX_STATION_KM}


def _trip(trip_id):
    if not ObjectId.is_valid(trip_id):
        raise HTTPException(422, "Invalid trip_id: expected a MongoDB ObjectId")
    rows = list(tripDetailsService.collection.aggregate([
        {"$match": {"_id": ObjectId(trip_id), **tripDetailsService._active_trip_filter()}},
        {"$project": {"_id": {"$toString": "$_id"}, "water_type": 1, "lake_locations": 1, "area_fished": 1}},
    ]))
    if not rows:
        raise HTTPException(404, "Trip details not found")
    if rows[0].get("water_type") != 4:
        raise HTTPException(422, "Coastal conditions require a coastal trip (water_type 4)")
    return rows[0]


def _location(trip):
    userTripService._expand_lake_locations([trip])
    for location in trip["lake_locations"]:
        lat, lon = _number(location.get("latitude")), _number(location.get("longitude"))
        if lat is not None and lon is not None and -90 <= lat <= 90 and -180 <= lon <= 180:
            return {"location_id": str(location["_id"]), "name": location.get("name"),
                    "state": location.get("state"), "latitude": lat, "longitude": lon,
                    "selection": "First saved trip map location with valid coordinates"}
    raise HTTPException(422, "The coastal trip needs a saved map location with valid latitude and longitude")


def _response(trip_id):
    saved = collection.find_one({"_id": ObjectId(trip_id)}, {"_id": 0, "start": 1, "end": 1}) or {}
    return {"status": "success", "data": {"trip_id": trip_id,
            "start": saved.get("start"), "end": saved.get("end")}}


def capture_conditions(trip_id, action):
    if action not in ("recapture_start", "capture_end"):
        raise HTTPException(422, "action must be recapture_start or capture_end")
    try:
        trip = _trip(trip_id)
        snapshot = _snapshot(_location(trip))
        slot = "start" if action == "recapture_start" else "end"
        # _id provides uniqueness; setting only one slot preserves concurrent writes to the other.
        collection.update_one({"_id": ObjectId(trip_id)}, {
            "$set": {slot: snapshot}, "$setOnInsert": {"created_at": _now().isoformat()},
        }, upsert=True)
        return _response(trip_id)
    except PyMongoError:
        raise HTTPException(503, "Unable to load or save coastal conditions") from None


def get_conditions(trip_id):
    try:
        _trip(trip_id)
        return _response(trip_id)
    except PyMongoError:
        raise HTTPException(503, "Unable to load coastal conditions") from None
