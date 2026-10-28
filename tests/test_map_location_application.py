import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from bson import ObjectId
from fastapi.testclient import TestClient

import main
from Models.MapLocation import MapLocationDropPinModel, MapLocationDropPinUpdateModel
from Services import locationService


class MapLocationApplicationTests(unittest.TestCase):
    def test_map_location_routes_are_registered(self):
        paths = {route.path for route in main.app.routes}

        self.assertIn("/map-locations/", paths)
        self.assertIn("/map-locations/{page}", paths)
        self.assertIn("/map-location/{map_location_id}", paths)

    def test_update_model_allows_partial_updates(self):
        update = MapLocationDropPinUpdateModel(name="Updated location")

        self.assertEqual(
            update.model_dump(exclude_unset=True), {"name": "Updated location"}
        )

    def test_create_map_location_returns_serializable_id(self):
        inserted_id = ObjectId()
        mock_collection = MagicMock()
        mock_collection.insert_one.return_value.inserted_id = inserted_id
        location = MapLocationDropPinModel(latitude="12.9716", longitude="77.5946")

        with patch.object(
            locationService, "map_location_collection", mock_collection
        ):
            result = locationService.create_map_location(location)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["_id"], str(inserted_id))
        self.assertIs(result["data"]["is_favorite"], False)

    def test_delete_map_location_is_a_soft_delete(self):
        map_location_id = str(ObjectId())
        mock_collection = MagicMock()
        mock_collection.update_one.return_value.matched_count = 1

        with patch.object(
            locationService, "map_location_collection", mock_collection
        ):
            result = locationService.delete_map_location(map_location_id, "admin-id")

        self.assertEqual(result["status"], "success")
        update = mock_collection.update_one.call_args.args[1]["$set"]
        self.assertEqual(update["deleted_by"], "admin-id")
        self.assertIn("deleted_at", update)
        self.assertIsInstance(update["deleted_at"], datetime)
        self.assertEqual(update["deleted_at"].tzinfo, timezone.utc)

    def test_create_route_stores_all_drop_pin_fields(self):
        payload = {
            "latitude": 37.2089, "longitude": -93.2923,
            "pin_type": "weed_bed", "water_body_id": "lake_123",
            "target_species": ["common_carp", "gar"], "water_depth_ft": 4.5,
            "notes": "Fish near the reeds",
            "is_favorite": True,
            "privacy": "friend-only",
        }
        mock_collection = MagicMock()
        mock_collection.insert_one.return_value.inserted_id = ObjectId()
        with patch.object(locationService, "map_location_collection", mock_collection):
            response = TestClient(main.app).post("/map-locations/", json=payload)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")
        stored = mock_collection.insert_one.call_args.args[0]
        for key, value in payload.items():
            self.assertEqual(stored[key], value)
            self.assertEqual(response.json()["data"][key], value)
        self.assertIsInstance(stored["created_at"], datetime)

    def test_routes_validate_drop_pin_fields_before_writing(self):
        client = TestClient(main.app)
        with patch.object(locationService, "map_location_collection") as collection:
            for invalid in (
                {"latitude": 91}, {"longitude": -181},
                {"pin_type": "invalid"}, {"water_depth_ft": -1},
                {"target_species": "carp"},
                {"is_favorite": "invalid"},
                {"privacy": "invalid"},
            ):
                with self.subTest(invalid=invalid):
                    payload = {"latitude": 37.2, "longitude": -93.2, **invalid}
                    self.assertEqual(client.post("/map-locations/", json=payload).status_code, 422)
                    self.assertEqual(client.put(f"/map-location/{ObjectId()}", json=invalid).status_code, 422)
            collection.insert_one.assert_not_called()
            collection.update_one.assert_not_called()

    def test_partial_update_can_clear_pin_details_without_resetting_coordinates(self):
        payload = {"pin_type": "rock_pile", "target_species": [], "water_depth_ft": None, "notes": None, "privacy": "private"}
        mock_collection = MagicMock()
        with patch.object(locationService, "map_location_collection", mock_collection):
            response = TestClient(main.app).put(f"/map-location/{ObjectId()}", json=payload)

        self.assertEqual(response.json()["status"], "success")
        changes = mock_collection.update_one.call_args.args[1]["$set"]
        updated_at = changes.pop("updated_at")
        self.assertEqual(changes, payload)
        self.assertEqual(updated_at.tzinfo, timezone.utc)

    def test_update_route_can_mark_and_unmark_favorites(self):
        client = TestClient(main.app)
        with patch.object(locationService, "map_location_collection") as collection:
            for value in (True, False):
                with self.subTest(is_favorite=value):
                    response = client.put(
                        f"/map-location/{ObjectId()}", json={"is_favorite": value}
                    )
                    self.assertEqual(response.json()["status"], "success")
                    changes = collection.update_one.call_args.args[1]["$set"]
                    self.assertIs(changes["is_favorite"], value)
                    self.assertEqual(set(changes), {"is_favorite", "updated_at"})

    def test_list_and_detail_reads_include_drop_pin_fields(self):
        fields = {"pin_type", "water_body_id", "target_species", "water_depth_ft", "notes", "is_favorite", "privacy"}
        mock_collection = MagicMock()
        mock_collection.aggregate.return_value = []
        with patch.object(locationService, "map_location_collection", mock_collection), patch.object(
            locationService, "paginate", return_value={"data": [], "total": 0}
        ) as paginate:
            locationService.get_map_locations(1, 10)
            list_pipeline = paginate.call_args.args[1]
            locationService.get_map_location_by_id(str(ObjectId()))
            detail_pipeline = mock_collection.aggregate.call_args.args[0]

        for pipeline in (list_pipeline, detail_pipeline):
            projection = next(stage["$project"] for stage in pipeline if "$project" in stage)
            self.assertTrue(fields.issubset(projection))
            self.assertEqual(projection["is_favorite"], {"$ifNull": ["$is_favorite", False]})
            self.assertEqual(pipeline[0]["$match"]["deleted_at"], {"$in": ["", None]})


if __name__ == "__main__":
    unittest.main()
