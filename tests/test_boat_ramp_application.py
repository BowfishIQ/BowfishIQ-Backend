import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from bson import ObjectId
from fastapi.testclient import TestClient

import main
from Services import boatRampService


class BoatRampApplicationTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(main.app)
        self.collection = MagicMock()
        collection_patch = patch.object(boatRampService, "boat_ramp_collection", self.collection)
        collection_patch.start()
        self.addCleanup(collection_patch.stop)
        self.ramp_id = str(ObjectId())
        self.path = f"/boat-ramp/{self.ramp_id}"

    def test_create_stores_ramp_fields_and_returns_serializable_id(self):
        self.collection.insert_one.return_value.inserted_id = ObjectId(self.ramp_id)
        payload = {
            "name": "North Ramp", "lake_river": "Stockton Lake",
            "latitude": 37.2, "longitude": -93.2, "ramp_type": "public",
            "parking_type": "ample", "condition": "good", "night_access": True,
            "fee": 0, "dock_availability": True, "bathroom_availability": False,
            "notes": "Open all night", "post_anonymous": False, "user_id": "user-1",
        }
        response = self.client.post("/boat-ramps/", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")
        data = response.json()["data"]
        self.assertEqual(data["_id"], self.ramp_id)
        stored = self.collection.insert_one.call_args.args[0]
        for key, value in payload.items():
            self.assertEqual(data[key], value)
            self.assertEqual(stored[key], value)
        self.assertEqual(stored["created_at"].tzinfo, timezone.utc)

    def test_list_paginates_filters_searches_and_excludes_deleted_records(self):
        self.collection.aggregate.return_value = [{"data": [], "total": [{"count": 7}]}]
        response = self.client.get("/boat-ramps/2", params={
            "limit": 3, "status": 1, "search_query": "Stockton",
        })
        data = response.json()["data"]
        self.assertEqual((data["page"], data["total"], data["totalPages"]), (2, 7, 3))
        facet = self.collection.aggregate.call_args.args[0][0]["$facet"]
        query = facet["data"][0]["$match"]
        self.assertEqual(query["status"], 1)
        self.assertEqual(query["deleted_at"], {"$in": ["", None]})
        self.assertIn({"lake_river": {"$regex": "Stockton", "$options": "i"}}, query["$or"])
        self.assertEqual(facet["data"][-2:], [{"$skip": 3}, {"$limit": 3}])

    def test_read_returns_ramp_and_projects_its_fields(self):
        ramp = {"_id": self.ramp_id, "lake_river": "Stockton Lake", "fee": 0}
        self.collection.aggregate.return_value = [ramp]
        self.assertEqual(self.client.get(self.path).json()["data"], ramp)
        pipeline = self.collection.aggregate.call_args.args[0]
        self.assertEqual(pipeline[0]["$match"], {
            "_id": ObjectId(self.ramp_id), "deleted_at": {"$in": ["", None]},
        })
        from Models.BoatRamp import BoatRampModel
        readable_fields = set(BoatRampModel.model_fields) - {"deleted_at", "deleted_by"}
        self.assertTrue(readable_fields.issubset(pipeline[1]["$project"]))

    def test_update_preserves_omitted_fields_and_accepts_false_zero_and_null(self):
        payload = {"lake_river": "New Lake", "fee": 0, "night_access": False, "notes": None}
        self.assertEqual(self.client.put(self.path, params={"user_id": "user-1"}, json=payload).json()["status"], "success")
        changes = self.collection.update_one.call_args.args[1]["$set"]
        self.assertEqual(changes.pop("updated_at").tzinfo, timezone.utc)
        self.assertEqual(changes.pop("updated_by"), "user-1")
        self.assertEqual(changes, payload)

    def test_empty_update_does_not_write(self):
        self.assertEqual(self.client.put(self.path, params={"user_id": "user-1"}, json={}).json()["status"], "error")
        self.collection.update_one.assert_not_called()

    def test_delete_is_soft_and_records_actor_and_utc_time(self):
        self.collection.update_one.return_value.matched_count = 1
        result = self.client.delete(self.path, params={"user_id": "user-1"}).json()
        self.assertEqual(result["status"], "success")
        query, update = self.collection.update_one.call_args.args
        self.assertEqual(query["deleted_at"], {"$in": ["", None]})
        self.assertEqual(update["$set"]["deleted_by"], "user-1")
        self.assertIsInstance(update["$set"]["deleted_at"], datetime)
        self.assertEqual(update["$set"]["deleted_at"].tzinfo, timezone.utc)
        self.collection.delete_one.assert_not_called()

    def test_invalid_ids_do_not_access_database(self):
        for method, kwargs in (("get", {}), ("put", {"json": {"name": "Ramp"}, "params": {"user_id": "user-1"}}), ("delete", {"params": {"user_id": "user-1"}})):
            self.assertEqual(getattr(self.client, method)("/boat-ramp/invalid", **kwargs).json()["status"], "error")
        self.assertEqual(self.collection.mock_calls, [])

    def test_missing_or_deleted_ramps_return_errors(self):
        self.collection.aggregate.return_value = []
        self.collection.find_one.return_value = None
        self.collection.update_one.return_value.matched_count = 0
        self.assertEqual(self.client.get(self.path).json()["status"], "error")
        self.assertEqual(self.client.put(self.path, params={"user_id": "user-1"}, json={"name": "Ramp"}).json()["status"], "error")
        self.collection.update_one.assert_not_called()
        self.assertEqual(self.client.delete(self.path, params={"user_id": "user-1"}).json()["status"], "error")

    def test_invalid_pagination_does_not_access_database(self):
        for path in ("/boat-ramps/0", "/boat-ramps/1?limit=0"):
            self.assertEqual(self.client.get(path).json()["status"], "error")
        self.assertEqual(self.collection.mock_calls, [])

    def test_invalid_coordinates_are_rejected_before_writes(self):
        for payload in ({}, {"latitude": 91, "longitude": 0}, {"latitude": 0, "longitude": -181}):
            self.assertEqual(self.client.post("/boat-ramps/", json=payload).status_code, 422)
        self.assertEqual(self.client.put(self.path, params={"user_id": "user-1"}, json={"latitude": 91}).status_code, 422)
        self.assertEqual(self.collection.mock_calls, [])


if __name__ == "__main__":
    unittest.main()
