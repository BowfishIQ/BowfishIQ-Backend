import unittest
from datetime import timezone
from unittest.mock import MagicMock, patch

from bson import ObjectId
from fastapi.testclient import TestClient

import main
from Services import lakesService


class LakesApplicationTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(main.app)
        self.collection = MagicMock()
        collection_patch = patch.object(lakesService, "lake_collection", self.collection)
        collection_patch.start()
        self.addCleanup(collection_patch.stop)
        self.lake_id = str(ObjectId())
        self.path = f"/lake/{self.lake_id}"
        self.owner = {"user_id": "user-1"}
        self.collection.insert_one.return_value.inserted_id = ObjectId(self.lake_id)
        self.collection.update_one.return_value.matched_count = 1

    def test_create_preserves_fields_and_controls_audit_fields(self):
        payload = {
            **self.owner, "name": "Stockton", "country": "United States",
            "state": ["Missouri", "Kansas"], "city": "Stockton", "zip_code": "65785",
            "latitude": 37.2, "longitude": -93.2, "water_type": "Lake",
            "gauge_data": "station-1", "notes": "Public access", "status": 0,
            "created_at": "2000-01-01T00:00:00Z", "deleted_by": "other",
            "deleted_at": "2000-01-01T00:00:00Z",
        }
        response = self.client.post("/lakes/", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["_id"], self.lake_id)
        stored = self.collection.insert_one.call_args.args[0]
        for field, value in payload.items():
            if field not in ("created_at", "deleted_at", "deleted_by"):
                self.assertEqual(stored[field], value)
        self.assertIsNone(stored["deleted_at"])
        self.assertIsNone(stored["deleted_by"])
        self.assertEqual(stored["created_at"].tzinfo, timezone.utc)
        self.assertGreater(stored["created_at"].year, 2000)

    def test_optional_fields_and_state_lengths(self):
        for state in (None, [], ["Missouri"], ["Missouri", "Kansas"]):
            response = self.client.post("/lakes/", json={"state": state})
            self.assertEqual(response.json()["status"], "success")

    def test_invalid_fields_are_rejected_without_writes(self):
        for payload in (
            {"state": ["A", "B", "C"]}, {"state": "Missouri"},
            {"latitude": 91}, {"longitude": -181}, {"status": 3},
        ):
            self.assertEqual(self.client.post("/lakes/", json=payload).status_code, 422)
        for payload in ({"state": ["A", "B", "C"]}, {"latitude": -91}):
            self.assertEqual(self.client.put(self.path, params=self.owner, json=payload).status_code, 422)
        self.collection.insert_one.assert_not_called()
        self.collection.update_one.assert_not_called()

    def test_water_data_validates_id_and_existing_undeleted_reference(self):
        response = self.client.post("/lakes/", json={"water_data": "invalid"})
        self.assertEqual(response.json()["status"], "error")
        self.collection.find_one.assert_not_called()
        self.collection.find_one.return_value = None
        response = self.client.post("/lakes/", json={"water_data": self.lake_id})
        self.assertEqual(response.json()["status"], "error")
        self.collection.insert_one.assert_not_called()
        self.assertEqual(self.collection.find_one.call_args.args[0], {
            "_id": ObjectId(self.lake_id), "deleted_at": {"$in": ["", None]},
        })
        self.collection.find_one.return_value = {"_id": ObjectId(self.lake_id)}
        response = self.client.post("/lakes/", json={"water_data": self.lake_id})
        self.assertEqual(response.json()["data"]["water_data"], self.lake_id)

    def test_list_filters_searches_and_paginates(self):
        self.collection.aggregate.return_value = [{"data": [], "total": [{"count": 7}]}]
        result = self.client.get("/lakes/2", params={
            **self.owner, "limit": 3, "status": 1, "search_query": "Stockton",
        }).json()
        self.assertEqual((result["data"]["total"], result["data"]["totalPages"]), (7, 3))
        facet = self.collection.aggregate.call_args.args[0][0]["$facet"]
        query = facet["data"][0]["$match"]
        self.assertEqual(query["user_id"], "user-1")
        self.assertEqual(query["status"], 1)
        self.assertEqual(query["deleted_at"], {"$in": ["", None]})
        self.assertIn({"state": {"$regex": "Stockton", "$options": "i"}}, query["$or"])
        self.assertEqual(facet["data"][-2:], [{"$skip": 3}, {"$limit": 3}])

    def test_read_projects_lake_fields_and_filters_owner(self):
        lake = {"_id": self.lake_id, "state": ["Missouri"]}
        self.collection.aggregate.return_value = [lake]
        self.assertEqual(self.client.get(self.path, params=self.owner).json()["data"], lake)
        pipeline = self.collection.aggregate.call_args.args[0]
        self.assertEqual(pipeline[0]["$match"]["user_id"], "user-1")
        self.assertIn("water_data", pipeline[1]["$project"])
        self.assertIn("gauge_data", pipeline[1]["$project"])
        self.collection.aggregate.return_value = []
        self.assertEqual(self.client.get(self.path).json()["status"], "error")

    def test_partial_update_preserves_owner_and_omitted_fields(self):
        payload = {"user_id": "other", "latitude": 0, "notes": None, "state": []}
        response = self.client.put(self.path, params=self.owner, json=payload)
        self.assertEqual(response.json()["status"], "success")
        query, update = self.collection.update_one.call_args.args
        self.assertEqual(query["user_id"], "user-1")
        changes = update["$set"]
        self.assertEqual(changes.pop("updated_at").tzinfo, timezone.utc)
        self.assertEqual(changes.pop("updated_by"), "user-1")
        self.assertEqual(changes, {"latitude": 0, "notes": None, "state": []})

    def test_update_rejects_missing_owner_record_empty_update_and_bad_reference(self):
        for payload in ({}, {"user_id": "other"}, {"water_data": "bad-id"}):
            response = self.client.put(self.path, params=self.owner, json=payload)
            self.assertEqual(response.json()["status"], "error")
        self.collection.find_one.side_effect = [{"user_id": "user-1"}, None]
        response = self.client.put(self.path, params=self.owner, json={"water_data": self.lake_id})
        self.assertEqual(response.json()["status"], "error")
        self.collection.find_one.side_effect = None
        self.collection.find_one.return_value = None
        response = self.client.put(self.path, params=self.owner, json={"name": "New"})
        self.assertEqual(response.json()["status"], "error")
        self.collection.update_one.assert_not_called()

    def test_soft_delete_checks_owner_and_records_actor(self):
        response = self.client.delete(self.path, params=self.owner)
        self.assertEqual(response.json()["status"], "success")
        query, update = self.collection.update_one.call_args.args
        self.assertEqual(query, {
            "_id": ObjectId(self.lake_id), **self.owner,
            "deleted_at": {"$in": ["", None]},
        })
        self.assertEqual(update["$set"]["deleted_by"], "user-1")
        self.assertEqual(update["$set"]["deleted_at"].tzinfo, timezone.utc)
        self.collection.delete_one.assert_not_called()
        self.collection.update_one.return_value.matched_count = 0
        self.assertEqual(self.client.delete(self.path, params=self.owner).json()["status"], "error")

    def test_missing_or_blank_actor_is_rejected(self):
        for params in ({}, {"user_id": ""}, {"user_id": "   "}):
            self.assertEqual(self.client.put(self.path, params=params, json={"name": "New"}).status_code, 422)
            self.assertEqual(self.client.delete(self.path, params=params).status_code, 422)
        self.assertEqual(self.collection.mock_calls, [])

    def test_invalid_ids_and_pagination_do_not_access_database(self):
        for method, kwargs in (
            ("get", {}), ("put", {"params": self.owner, "json": {"name": "New"}}),
            ("delete", {"params": self.owner}),
        ):
            self.assertEqual(getattr(self.client, method)("/lake/invalid", **kwargs).json()["status"], "error")
        for path in ("/lakes/0", "/lakes/1?limit=0"):
            self.assertEqual(self.client.get(path).json()["status"], "error")
        self.assertEqual(self.collection.mock_calls, [])


if __name__ == "__main__":
    unittest.main()
