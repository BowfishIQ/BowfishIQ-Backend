import json
import unittest
from unittest.mock import MagicMock, patch

from bson import ObjectId
from fastapi.testclient import TestClient

import main
from Services import boatRampService, locationService, publicReportService


class RecordUserOwnershipTests(unittest.TestCase):
    resources = (
        (locationService, "map_location_collection", "map-locations", "map-location"),
        (boatRampService, "boat_ramp_collection", "boat-ramps", "boat-ramp"),
        (publicReportService, "public_report_collection", "public-reports", "public-report"),
    )

    def setUp(self):
        self.client = TestClient(main.app)
        self.record_id = str(ObjectId())
        self.owner = str(ObjectId())

    def write(self, method, path, payload, **request_kwargs):
        # Public reports retain their existing multipart JSON + image interface.
        kwargs = ({"data": {"public_report": json.dumps(payload)}}
                  if "public-report" in path else {"json": payload})
        return getattr(self.client, method)(path, **kwargs, **request_kwargs)

    def test_create_accepts_optional_owner_for_every_resource(self):
        for service, attr, plural, _ in self.resources:
            for owner in (None, self.owner):
                with self.subTest(resource=plural, owner=owner), patch.object(service, attr) as collection:
                    collection.insert_one.return_value.inserted_id = ObjectId(self.record_id)
                    payload = {"latitude": 12, "longitude": 77}
                    if owner is not None:
                        payload["user_id"] = owner
                    response = self.write("post", f"/{plural}/", payload)
                    self.assertEqual(response.status_code, 200, response.text)
                    self.assertEqual(response.json()["status"], "success", response.text)
                    self.assertEqual(collection.insert_one.call_args.args[0]["user_id"], owner)

    def test_list_and_detail_filter_owner_and_join_profile(self):
        for service, attr, plural, singular in self.resources:
            with self.subTest(resource=plural), patch.object(service, attr) as collection:
                collection.aggregate.return_value = [{"data": [], "total": []}]
                response = self.client.get(f"/{plural}/1", params={"user_id": self.owner})
                self.assertEqual(response.json()["status"], "success")
                facet = collection.aggregate.call_args.args[0][0]["$facet"]
                self.assertEqual(facet["data"][0]["$match"]["user_id"], self.owner)
                self.assertEqual(facet["total"][0]["$match"]["user_id"], self.owner)
                profile = {"_id": self.owner, "first_name": "Sam"}
                collection.aggregate.return_value = [{"_id": self.record_id, "user_details": profile}]
                response = self.client.get(f"/{singular}/{self.record_id}", params={"user_id": self.owner})
                self.assertEqual(response.json()["data"]["user_details"], profile)
                pipeline = collection.aggregate.call_args.args[0]
                self.assertEqual(pipeline[0]["$match"]["user_id"], self.owner)
                lookup = next(stage["$lookup"] for stage in pipeline if "$lookup" in stage)
                self.assertEqual(lookup["from"], "user")
                fields = lookup["pipeline"][-1]["$project"]
                self.assertIn("first_name", fields)
                self.assertNotIn("password", fields)
                self.assertNotIn("firebase_token", fields)

    def test_update_checks_owner_and_records_actor_without_transferring_ownership(self):
        for service, attr, _, singular in self.resources:
            with self.subTest(resource=singular), patch.object(service, attr) as collection:
                collection.find_one.side_effect = lambda query: (
                    {"user_id": self.owner} if query.get("user_id") == self.owner else None
                )
                collection.update_one.return_value.matched_count = 1
                path = f"/{singular}/{self.record_id}"
                payload = {"name": "Updated", "latitude": 12, "longitude": 77, "user_id": "other-user"}
                response = self.write("put", path, payload, params={"user_id": "other-user"})
                self.assertEqual(response.json()["status"], "error", response.text)
                collection.update_one.assert_not_called()
                # A conflicting body ID cannot override the query parameter.
                response = self.write("put", path, payload, params={"user_id": self.owner})
                self.assertEqual(response.json()["status"], "success", response.text)
                query, update = collection.update_one.call_args.args
                self.assertEqual(query["user_id"], self.owner)
                self.assertEqual(update["$set"]["updated_by"], self.owner)
                self.assertNotIn("user_id", update["$set"])

    def test_delete_checks_owner_atomically_and_records_actor(self):
        for service, attr, _, singular in self.resources:
            with self.subTest(resource=singular), patch.object(service, attr) as collection:
                collection.update_one.side_effect = lambda query, update: MagicMock(
                    matched_count=int(query.get("user_id") == self.owner)
                )
                path = f"/{singular}/{self.record_id}"
                response = self.client.delete(path, params={"user_id": "other-user"})
                self.assertEqual(response.json()["status"], "error")
                response = self.client.delete(path, params={"user_id": self.owner})
                self.assertEqual(response.json()["status"], "success")
                query, update = collection.update_one.call_args.args
                self.assertEqual(query["user_id"], self.owner)
                self.assertEqual(update["$set"]["deleted_by"], self.owner)
                self.assertIn("deleted_at", update["$set"])

    def test_missing_or_blank_query_owner_cannot_bypass_verification(self):
        for service, attr, _, singular in self.resources:
            with self.subTest(resource=singular), patch.object(service, attr) as collection:
                path = f"/{singular}/{self.record_id}"
                payload = {"name": "Updated", "latitude": 12, "longitude": 77, "user_id": self.owner}
                for params in ({}, {"user_id": ""}, {"user_id": "   "}, {"deleted_by": self.owner}):
                    response = self.write("put", path, payload, params=params)
                    self.assertEqual(response.status_code, 422, response.text)
                    response = self.client.delete(path, params=params)
                    self.assertEqual(response.status_code, 422, response.text)
                collection.find_one.assert_not_called()
                collection.update_one.assert_not_called()

    def test_openapi_exposes_required_query_owner_and_no_delete_actor_parameter(self):
        schema = self.client.get("/openapi.json").json()
        for _, _, _, singular in self.resources:
            path = next(path for path in schema["paths"] if path.startswith(f"/{singular}/"))
            for method in ("put", "delete"):
                params = {param["name"]: param for param in schema["paths"][path][method]["parameters"]}
                self.assertEqual(params["user_id"]["in"], "query")
                self.assertTrue(params["user_id"]["required"])
                self.assertNotIn("deleted_by", params)


if __name__ == "__main__":
    unittest.main()
