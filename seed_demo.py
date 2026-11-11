"""Generate one demo team's data; database insertion requires --apply."""

import argparse
from pathlib import Path

import bcrypt
from bson import ObjectId, json_util

from Models.MapLocation import MapLocationDropPinModel
from Models.TripDetails import TripDetailsModel
from Models.User import UserModel


TEAM_NAME = "River Arrow Crew"
DEMO_PASSWORD = "BowfishDemo@123"
SEED_MARKER = "demo:river-arrow-crew:v1"
OUTPUT_DIR = Path(__file__).resolve().parent / "docs" / "demo-data"
USER_IDS = [str(ObjectId(f"bf10000000000000000000{i:02x}")) for i in range(1, 8)]
TRIP_IDS = [str(ObjectId(f"bf20000000000000000000{i:02x}")) for i in range(1, 6)]
LOCATION_IDS = [str(ObjectId(f"bf30000000000000000000{i:02x}")) for i in range(1, 3)]
MEMBERS = [
    ("Alex", "Morgan"), ("Jamie", "Reed"), ("Taylor", "Brooks"),
    ("Jordan", "Hayes"), ("Casey", "Parker"), ("Riley", "Bennett"),
    ("Sam", "Carter"),
]


def _timestamps(date, time="12:00:00"):
    return {"created_at": f"{date} {time}", "created_date": date, "created_time": time}


def build_demo_data():
    password_hash = bcrypt.hashpw(DEMO_PASSWORD.encode(), bcrypt.gensalt()).decode()
    users = []
    for user_id, (first, last) in zip(USER_IDS, MEMBERS):
        user = UserModel(
            name=f"{first} {last}", first_name=first, last_name=last,
            email=f"{first.lower()}.{last.lower()}@example.com",
            password=password_hash, login_type=2, user_role=2,
            verification_status=1, payment_status=1, status=1,
            created_by=SEED_MARKER, **_timestamps("2026-09-20"),
        ).model_dump()
        users.append({"_id": ObjectId(user_id), **user})

    locations = []
    for location_id, name, latitude, longitude in zip(
        LOCATION_IDS,
        ("Demo Lake - North Cove", "Demo River - South Bend"),
        ("38.2500", "38.1800"), ("-93.4000", "-93.3500"),
    ):
        location = MapLocationDropPinModel(
            name=name, country="United States", state="Missouri", city="Demo City",
            zip_code="00000", latitude=latitude, longitude=longitude,
            created_at="2026-09-20T12:00:00Z",
        ).model_dump()
        locations.append({"_id": ObjectId(location_id), **location, "created_by": SEED_MARKER})

    # Each trip includes the same seven members, with a rotating captain.
    roles = ["1", "2", "2", "3", "4", "5", "2"]
    scenarios = [
        ("2026-09-25", 1, 0, 1, [12, 4, 2], 7, 18.5, 34.0),
        ("2026-09-28", 2, 1, 2, [0, 0, 0], 26, 0, 0),
        ("2026-10-02", 1, 2, 2, [15, 6, 3], 10, 21.0, 38.0),
        ("2026-10-07", 2, 0, 1, [0, 0, 0], 32, 0, 0),
        ("2026-10-11", 1, 3, 1, [20, 7, 4], 12, 24.5, 42.0),
    ]
    trips = []
    for index, (date, trip_type, captain, water_type, catches, seen, weight, length) in enumerate(scenarios):
        trip_roles = [roles[(member - captain) % len(roles)] for member in range(7)]
        catch_total = sum(catches)
        # Distribute the demo shot total among the three shooters.
        shooters = [member for member, role in enumerate(trip_roles) if role == "2"]
        shots = {member: catch_total // 3 + (position < catch_total % 3)
                 for position, member in enumerate(shooters)}
        fish = [{
            "fish_id": None, "name": name, "count": count,
            "largest_fish": round(weight * factor, 1),
            "largest_fish_length": round(length * factor, 1), "status": 1,
        } for name, count, factor in zip(("Carp", "Buffalo", "Gar"), catches, (1, 0.9, 0.8)) if count]
        trip = TripDetailsModel(
            user_id=USER_IDS[captain],
            crew_details=[{"user_id": user_id, "user_name": user["name"], "user_role": [role], "status": 1}
                          for user_id, user, role in zip(USER_IDS, users, trip_roles)],
            team_details=[{"name": user["name"], "role": [role],
                           "shot_count": int(shots.get(member, 0)), "status": 1}
                          for member, (user, role) in enumerate(zip(users, trip_roles))],
            trip_type=trip_type, water_type=water_type, water_salinity=1,
            lake_locations=[LOCATION_IDS[water_type - 1]], lunch_ramp=str((index % 3) + 1),
            area_fished="North cove shallows" if water_type == 1 else "South river bend",
            date="-".join(reversed(date.split("-"))), start_time="18:30:00", end_time="22:30:00",
            fish_shot_details=fish, fish_see_not_shot_count=seen,
            water_temp=72.0 - index * 1.5, water_clarity=(index % 4) + 1,
            water_movement=1 if water_type == 1 else 2, wind=(index % 3) + 1,
            wind_speed=3.0 + index * 2, wind_direction=(index % 8) + 1,
            water_level=2, water_base=1, water_depth=4.0 + index,
            fish_location=[str((index % 5) + 1)],
            trip_outcome=f"Landed {catch_total} fish" if trip_type == 1 else "Scouted access and fish activity; no fish shot",
            trip_lessons="Shallow sheltered water had the best visibility.",
            trip_notes=f"{SEED_MARKER} | Team: {TEAM_NAME} | Demo trip {index + 1}",
            images=[], status=1, created_by=USER_IDS[captain],
            **_timestamps(date, "23:00:00"),
        ).model_dump()
        trips.append({"_id": ObjectId(TRIP_IDS[index]), **trip})
    return {"user": users, "map_location": locations, "trip_details": trips}


def export_demo_data(data, output_dir=OUTPUT_DIR):
    output_dir.mkdir(parents=True, exist_ok=True)
    for collection, documents in data.items():
        (output_dir / f"{collection}.json").write_text(
            json_util.dumps(documents, indent=2) + "\n", encoding="utf-8",
        )
    manifest = {
        "team_name": TEAM_NAME, "demo_password": DEMO_PASSWORD,
        "users": [{"id": str(user["_id"]), "name": user["name"], "email": user["email"]}
                  for user in data["user"]],
        "trip_ids": TRIP_IDS, "location_ids": LOCATION_IDS,
        "expected_all_team_summary": {
            "total_trips": 5, "regular_trips": 3, "scouting_trips": 2,
            "total_fish_caught": 73, "total_team_shots": 73,
            "total_fish_seen_not_shot": 87, "total_crew_entries": 35,
            "total_team_entries": 35,
            "fish_counts": {"Carp": 47, "Buffalo": 17, "Gar": 9},
        },
        "expected_alex_role_counts": {"captain": 2, "shooter": 1, "spotter": 0, "guest": 1, "other": 1},
        "example_list": f"/users/{USER_IDS[0]}/trip-details?page=1&limit=2",
        "example_summary": f"/users/{USER_IDS[0]}/trip-details/summary",
    }
    (output_dir / "manifest.json").write_text(json_util.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def insert_demo_data(database, data):
    """Preflight collisions, then insert missing documents without overwriting."""
    pending = []
    counts = {}
    for name, documents in data.items():
        counts[name] = {"inserted": 0, "skipped": 0}
        for document in documents:
            existing = database[name].find_one({"_id": document["_id"]})
            if existing:
                identity_field = "trip_notes" if name == "trip_details" else "created_by"
                if existing.get(identity_field) != document[identity_field]:
                    raise ValueError(f"Seed ID collision in {name}: {document['_id']}")
                counts[name]["skipped"] += 1
            else:
                if name == "user" and database[name].find_one({"email": document["email"]}):
                    raise ValueError(f"Email already belongs to another user: {document['email']}")
                pending.append((name, document))
    for name, document in pending:
        database[name].insert_one(document)
        counts[name]["inserted"] += 1
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Insert missing demo records into the database configured in db.py")
    args = parser.parse_args()
    data = build_demo_data()
    export_demo_data(data)
    print(f"Generated {TEAM_NAME}: 7 users, 5 trips, 2 map locations in {OUTPUT_DIR}")
    if args.apply:
        from db import db
        print(insert_demo_data(db, data))
    else:
        print("Local files only. To insert into the configured database: python seed_demo.py --apply")


if __name__ == "__main__":
    main()
