import unittest
from collections import Counter
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest.mock import MagicMock

import bcrypt
from bson import json_util

from Models.TripDetails import TripDetailsModel
from Models.User import UserModel
from seed_demo import (
    DEMO_PASSWORD, USER_IDS, build_demo_data, export_demo_data, insert_demo_data,
)


class DemoSeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = build_demo_data()

    def test_seven_users_and_five_trips_have_valid_references_and_models(self):
        self.assertEqual(len(self.data["user"]), 7)
        self.assertEqual(len(self.data["trip_details"]), 5)
        users = {str(user["_id"]): user for user in self.data["user"]}
        locations = {str(location["_id"]) for location in self.data["map_location"]}
        self.assertEqual(len({user["email"] for user in users.values()}), 7)
        for user in users.values():
            UserModel.model_validate(user)
            self.assertTrue(bcrypt.checkpw(DEMO_PASSWORD.encode(), user["password"].encode()))
            self.assertEqual(user["login_type"], 2)
            self.assertEqual(user["verification_status"], 1)
        for trip in self.data["trip_details"]:
            TripDetailsModel.model_validate(trip)
            self.assertIn(trip["user_id"], users)
            self.assertTrue(set(trip["lake_locations"]).issubset(locations))
            self.assertEqual({crew["user_id"] for crew in trip["crew_details"]}, set(users))
            for crew, team in zip(trip["crew_details"], trip["team_details"]):
                self.assertEqual(users[crew["user_id"]]["name"], team["name"])
                self.assertEqual(crew["posuser_role"], team["role"])

    def test_export_preserves_object_ids_and_expected_summary(self):
        with TemporaryDirectory() as directory:
            export_demo_data(self.data, Path(directory))
            manifest = json_util.loads((Path(directory) / "manifest.json").read_text())
            exported = json_util.loads((Path(directory) / "trip_details.json").read_text())
            self.assertEqual(exported, self.data["trip_details"])
        trips = self.data["trip_details"]
        expected = manifest["expected_all_team_summary"]
        self.assertEqual(sum(trip["trip_type"] == 1 for trip in trips), expected["regular_trips"])
        self.assertEqual(sum(trip["trip_type"] == 2 for trip in trips), expected["scouting_trips"])
        self.assertEqual(sum(fish["count"] for trip in trips for fish in trip["fish_shot_details"]), expected["total_fish_caught"])
        self.assertEqual(sum(team["shot_count"] for trip in trips for team in trip["team_details"]), expected["total_team_shots"])
        self.assertEqual(sum(trip["fish_see_not_shot_count"] for trip in trips), expected["total_fish_seen_not_shot"])
        roles = Counter(crew["posuser_role"] for trip in trips for crew in trip["crew_details"] if crew["user_id"] == USER_IDS[0])
        self.assertEqual(roles, {"1": 2, "2": 1, "4": 1, "5": 1})

    def test_insert_is_repeatable_and_does_not_replace_existing_records(self):
        database = {name: MagicMock() for name in self.data}
        existing = {name: {} for name in self.data}
        for name in self.data:
            collection = database[name]
            collection.find_one.side_effect = lambda query, name=name: (
                existing[name].get(query["_id"]) if "_id" in query else
                next((doc for doc in existing[name].values() if doc.get("email") == query["email"]), None)
            )
            collection.insert_one.side_effect = lambda doc, name=name: existing[name].update({doc["_id"]: doc})
        first = insert_demo_data(database, self.data)
        second = insert_demo_data(database, self.data)
        self.assertEqual(first["user"], {"inserted": 7, "skipped": 0})
        self.assertEqual(second["user"], {"inserted": 0, "skipped": 7})
        self.assertEqual(second["trip_details"], {"inserted": 0, "skipped": 5})
        self.assertEqual(database["user"].insert_one.call_count, 7)

    def test_email_collision_is_detected_before_any_insert(self):
        database = {name: MagicMock() for name in self.data}
        database["user"].find_one.side_effect = lambda query: {"_id": "another-user"} if "email" in query else None
        with self.assertRaisesRegex(ValueError, "Email already belongs"):
            insert_demo_data(database, self.data)
        for name in self.data:
            database[name].insert_one.assert_not_called()


if __name__ == "__main__":
    unittest.main()
