import unittest
from unittest.mock import MagicMock, patch

from bson import ObjectId
from fastapi.testclient import TestClient

import main
from Models.TripDetails import (
    CrewDetailsModel, FishShotDetailsModel, TeamDetailsModel,
    TripDetailsModel, TripDetailsUpdateModel,
)
from Services import tripDetailsService


class TripDetailsApplicationTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(main.app)
        self.collection = MagicMock()
        collection_patch = patch.object(tripDetailsService, "collection", self.collection)
        collection_patch.start()
        self.addCleanup(collection_patch.stop)
        self.trip_id = str(ObjectId())

    def test_all_create_update_and_nested_fields_are_optional_and_nullable(self):
        for model in (TripDetailsModel, TripDetailsUpdateModel, CrewDetailsModel,
                      FishShotDetailsModel, TeamDetailsModel):
            with self.subTest(model=model.__name__):
                self.assertFalse(any(field.is_required() for field in model.model_fields.values()))
                model()
                model(**{field: None for field in model.model_fields})
        self.assertEqual(TripDetailsUpdateModel().model_dump(exclude_unset=True), {})

    def test_create_accepts_empty_object(self):
        self.collection.insert_one.return_value.inserted_id = ObjectId(self.trip_id)
        response = self.client.post("/trip-details/", json={})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["_id"], self.trip_id)
        self.assertEqual(response.json()["status"], "success")

    def test_create_serializes_optional_nested_details(self):
        self.collection.insert_one.return_value.inserted_id = ObjectId(self.trip_id)
        response = self.client.post("/trip-details/", json={
            "crew_details": [{}], "fish_shot_details": [{"count": 0}],
            "team_details": [{"name": "Captain"}],
        })
        self.assertEqual(response.json()["status"], "success")
        data = self.collection.insert_one.call_args.args[0]
        self.assertEqual(data["fish_shot_details"][0]["count"], 0)
        self.assertIsInstance(data["crew_details"][0], dict)

    def test_update_preserves_omitted_fields_and_allows_null_and_zero(self):
        self.collection.update_one.return_value.matched_count = 1
        response = self.client.put(f"/trip-detail/{self.trip_id}", json={
            "trip_notes": None, "fish_see_not_shot_count": 0, "status": 0,
        })
        self.assertEqual(response.json()["status"], "success")
        data = self.collection.update_one.call_args.args[1]["$set"]
        self.assertEqual(set(data), {
            "trip_notes", "fish_see_not_shot_count", "status", "updated_at",
        })
        self.assertIsNone(data["trip_notes"])
        self.assertEqual(data["fish_see_not_shot_count"], 0)
        self.assertEqual(data["status"], 0)

    def test_empty_update_does_not_write(self):
        response = self.client.put(f"/trip-detail/{self.trip_id}", json={})
        self.assertEqual(response.json()["status"], "error")
        self.collection.update_one.assert_not_called()

    def test_list_pagination_filters_and_excludes_deleted_trips(self):
        self.collection.aggregate.return_value = [{"data": [], "total": []}]
        response = self.client.get("/trip-details/2", params={
            "limit": 5, "status": 0, "user_id": "user-1", "search_query": "lake",
        })
        self.assertEqual(response.json()["status"], "success")
        pipeline = self.collection.aggregate.call_args.args[0][0]["$facet"]["data"]
        query = pipeline[0]["$match"]
        self.assertEqual(query["deleted_at"], {"$in": ["", None]})
        self.assertEqual(query["status"], 0)
        self.assertEqual(query["user_id"], "user-1")
        self.assertIn("$or", query)
        self.assertEqual(pipeline[-2:], [{"$skip": 5}, {"$limit": 5}])

    def test_invalid_pagination_does_not_query_database(self):
        response = self.client.get("/trip-details/0")
        self.assertEqual(response.json()["status"], "error")
        self.collection.aggregate.assert_not_called()

    def test_read_returns_trip_and_excludes_deleted_records(self):
        self.collection.aggregate.return_value = [{"_id": self.trip_id, "trip_notes": "Trip"}]
        response = self.client.get(f"/trip-detail/{self.trip_id}")
        self.assertEqual(response.json()["data"]["trip_notes"], "Trip")
        query = self.collection.aggregate.call_args.args[0][0]["$match"]
        self.assertEqual(query["deleted_at"], {"$in": ["", None]})

    def test_missing_trip_returns_errors_for_read_update_and_delete(self):
        self.collection.aggregate.return_value = []
        self.collection.update_one.return_value.matched_count = 0
        for response in (
            self.client.get(f"/trip-detail/{self.trip_id}"),
            self.client.put(f"/trip-detail/{self.trip_id}", json={"trip_notes": "New"}),
            self.client.delete(f"/trip-detail/{self.trip_id}"),
        ):
            self.assertEqual(response.json()["message"], "Trip details not found")

    def test_delete_is_soft_delete(self):
        self.collection.update_one.return_value.matched_count = 1
        response = self.client.delete(f"/trip-detail/{self.trip_id}", params={"deleted_by": "admin"})
        self.assertEqual(response.json()["status"], "success")
        data = self.collection.update_one.call_args.args[1]["$set"]
        self.assertEqual(data["deleted_by"], "admin")
        self.assertTrue(data["deleted_at"])
        self.collection.delete_one.assert_not_called()

    def test_invalid_ids_do_not_query_database(self):
        for response in (
            self.client.get("/trip-detail/invalid"),
            self.client.put("/trip-detail/invalid", json={"trip_notes": "New"}),
            self.client.delete("/trip-detail/invalid"),
        ):
            self.assertEqual(response.json()["message"], "Invalid trip details id")
        self.collection.aggregate.assert_not_called()
        self.collection.update_one.assert_not_called()


if __name__ == "__main__":
    unittest.main()
