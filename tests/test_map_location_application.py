import unittest
from unittest.mock import MagicMock, patch

from bson import ObjectId

import main
from Models.MapLocation import MapLocationModel, MapLocationUpdateModel
from Services import locationService


class MapLocationApplicationTests(unittest.TestCase):
    def test_map_location_routes_are_registered(self):
        paths = {route.path for route in main.app.routes}

        self.assertIn("/map-locations/", paths)
        self.assertIn("/map-locations/{page}", paths)
        self.assertIn("/map-location/{map_location_id}", paths)

    def test_update_model_allows_partial_updates(self):
        update = MapLocationUpdateModel(name="Updated location")

        self.assertEqual(
            update.model_dump(exclude_unset=True), {"name": "Updated location"}
        )

    def test_create_map_location_returns_serializable_id(self):
        inserted_id = ObjectId()
        mock_collection = MagicMock()
        mock_collection.insert_one.return_value.inserted_id = inserted_id
        location = MapLocationModel(latitude="12.9716", longitude="77.5946")

        with patch.object(
            locationService, "map_location_collection", mock_collection
        ):
            result = locationService.create_map_location(location)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["_id"], str(inserted_id))

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


if __name__ == "__main__":
    unittest.main()
