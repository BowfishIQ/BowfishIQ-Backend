import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

from bson import ObjectId
from fastapi.testclient import TestClient

import main
from Models.TripDetails import UserTripFilters
from Services import locationService, tripDetailsService, userTripService


class UserTripReportingTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(main.app, raise_server_exceptions=False)
        self.collection = MagicMock()
        collection_patch = patch.object(tripDetailsService, "collection", self.collection)
        collection_patch.start()
        self.addCleanup(collection_patch.stop)
        self.locations = MagicMock()
        location_patch = patch.object(locationService, "map_location_collection", self.locations)
        location_patch.start()
        self.addCleanup(location_patch.stop)
        self.user_id = str(ObjectId())
        self.base = f"/users/{self.user_id}/trip-details"
        self.collection.aggregate.return_value = [{"data": [], "total": []}]

    def test_lake_locations_return_full_details_in_reference_order(self):
        first, second = ObjectId(), ObjectId()
        first_location = {
            "_id": str(first), "name": "North Cove", "country": "United States",
            "state": "Missouri", "city": "Demo City", "zip_code": "00000",
            "latitude": "38.2500", "longitude": "-93.4000", "status": 1,
            "created_at": "2026-09-20 12:00:00", "created_by": ObjectId(self.user_id),
        }
        second_location = {"_id": str(second), "name": "South Bend", "latitude": "38.1800", "longitude": "-93.3500"}
        self.collection.aggregate.return_value = [{"data": [
            {"_id": "trip-1", "lake_locations": [str(second), str(first)]},
            {"_id": "trip-2", "lake_locations": [first]},
        ], "total": [{"count": 8}]}]
        self.locations.aggregate.return_value = [first_location, second_location]
        response = self.client.get(self.base, params={"page": 2, "limit": 2})
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["total"], 8)
        self.assertEqual(data["data"][0]["lake_locations"][0], second_location)
        self.assertEqual(data["data"][0]["lake_locations"][1]["state"], "Missouri")
        self.assertEqual(data["data"][1]["lake_locations"][0]["created_by"], self.user_id)
        self.locations.aggregate.assert_called_once()
        query = self.locations.aggregate.call_args.args[0][0]["$match"]
        self.assertEqual(set(query["_id"]["$in"]), {first, second})
        self.assertEqual(query["deleted_at"], {"$in": ["", None]})

    def test_missing_deleted_and_invalid_locations_are_omitted_without_losing_trip(self):
        missing, found = ObjectId(), ObjectId()
        self.collection.aggregate.return_value = [{"data": [{
            "_id": "trip-1", "lake_locations": [str(missing), "invalid", None, str(found)],
        }], "total": [{"count": 1}]}]
        self.locations.aggregate.return_value = [{"_id": str(found), "name": "Found"}]
        data = self.client.get(self.base).json()["data"]
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["data"][0]["lake_locations"], [{"_id": str(found), "name": "Found"}])

    def test_empty_null_or_missing_locations_return_empty_arrays_without_lookup(self):
        self.collection.aggregate.return_value = [{"data": [
            {"_id": "trip-1", "lake_locations": None},
            {"_id": "trip-2", "lake_locations": []},
            {"_id": "trip-3"},
            {"_id": "trip-4", "lake_locations": ["invalid"]},
        ], "total": [{"count": 4}]}]
        data = self.client.get(self.base).json()["data"]["data"]
        self.assertTrue(all(trip["lake_locations"] == [] for trip in data))
        self.locations.aggregate.assert_not_called()

    def test_list_pagination_and_legacy_object_ids(self):
        self.collection.aggregate.return_value = [{
            "data": [{"_id": "trip", "user_id": ObjectId(self.user_id),
                      "crew_details": [{"user_id": ObjectId(self.user_id)}]}],
            "total": [{"count": 12}],
        }]
        response = self.client.get(self.base, params={"page": 2, "limit": 5})
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual((data["total"], data["totalPages"]), (12, 3))
        self.assertEqual((data["start_count"], data["end_count"]), (5, 10))
        self.assertEqual(data["data"][0]["crew_details"][0]["user_id"], self.user_id)
        pipeline = self.collection.aggregate.call_args.args[0]
        query = pipeline[0]["$match"]
        self.assertEqual(query["$or"][0]["user_id"]["$in"], [self.user_id, ObjectId(self.user_id)])
        self.assertEqual(query["deleted_at"], {"$in": ["", None]})
        self.assertNotIn("$expr", query)
        self.assertEqual(pipeline[1]["$facet"]["data"][2:4], [{"$skip": 5}, {"$limit": 5}])

    def test_inclusive_range_uses_parsed_trip_dates_across_years(self):
        query = userTripService.build_user_trip_filter(self.user_id, UserTripFilters(
            start_date="31-12-2025", end_date="2026-01-02", scope="owner",
        ))
        self.assertNotIn("$or", query)
        comparisons = query["$expr"]["$and"]
        self.assertEqual(comparisons[1]["$gte"][1], datetime(2025, 12, 31))
        self.assertEqual(comparisons[2]["$lte"][1], datetime(2026, 1, 2))
        self.assertIn("$dateFromString", comparisons[1]["$gte"][0]["$ifNull"][0])

    def test_end_only_range_excludes_invalid_or_missing_dates(self):
        query = userTripService.build_user_trip_filter("user-1", UserTripFilters(end_date="2026-10-12"))
        self.assertEqual(query["$expr"]["$and"][0]["$ne"][1], None)
        self.assertIn("$lte", query["$expr"]["$and"][1])

    def test_exact_date_trip_id_and_simple_filters(self):
        trip_id = str(ObjectId())
        response = self.client.get(self.base, params={
            "date": "12-10-2026", "trip_id": trip_id, "scope": "crew",
            "trip_type": 2, "status": 0, "water_type": 3, "water_salinity": 1,
            "lake_location_id": "lake-1", "sort_order": "asc",
        })
        self.assertEqual(response.status_code, 200)
        pipeline = self.collection.aggregate.call_args.args[0]
        query = pipeline[0]["$match"]
        self.assertEqual(query["_id"], ObjectId(trip_id))
        self.assertEqual(query["trip_type"], 2)
        self.assertEqual(query["status"], 0)
        self.assertEqual(query["water_type"], 3)
        self.assertEqual(query["water_salinity"], 1)
        self.assertEqual(query["lake_locations"], {"$in": ["lake-1"]})
        self.assertEqual(query["crew_details"]["$elemMatch"]["status"], {"$in": [1, None]})
        self.assertEqual(query["$expr"]["$and"][1]["$eq"][1], datetime(2026, 10, 12))
        self.assertEqual(pipeline[1]["$facet"]["data"][1]["$sort"]["_id"], 1)

    def test_invalid_filters_do_not_query_database(self):
        shared_invalid = [
            {"date": "31-02-2026"}, {"date": "2026-1-1"}, {"date": ""},
            {"start_date": "2026-10-12", "end_date": "2026-10-01"},
            {"date": "2026-10-12", "start_date": "2026-10-01"},
            {"trip_id": "invalid"}, {"scope": "invalid"},
            {"trip_type": 0}, {"status": 3}, {"water_type": 5}, {"water_salinity": 4},
        ]
        for path in (self.base, self.base + "/summary"):
            for params in shared_invalid:
                with self.subTest(path=path, params=params):
                    self.assertEqual(self.client.get(path, params=params).status_code, 422)
        for params in ({"page": 0}, {"limit": 0}, {"limit": 101}, {"sort_order": "bad"}):
            self.assertEqual(self.client.get(self.base, params=params).status_code, 422)
        self.collection.aggregate.assert_not_called()

    def test_summary_uses_same_filters_and_does_not_paginate_or_multiply_trips(self):
        filters = {"start_date": "2026-01-01", "end_date": "2026-12-31", "trip_type": 2}
        self.client.get(self.base, params=filters)
        list_match = self.collection.aggregate.call_args.args[0][0]
        self.collection.aggregate.return_value = [{"totals": []}]
        response = self.client.get(self.base + "/summary", params=filters)
        self.assertEqual(response.status_code, 200)
        pipeline = self.collection.aggregate.call_args.args[0]
        self.assertEqual(pipeline[0], list_match)
        self.assertFalse(any("$unwind" in stage for stage in pipeline))
        facets = pipeline[-1]["$facet"]
        self.assertEqual(facets["totals"][0]["$group"]["total_trips"], {"$sum": 1})
        self.assertNotIn("$skip", str(facets))
        self.assertIn("$group", facets["user_role_counts"][2])

    def test_summary_returns_totals_roles_fish_and_breakdowns(self):
        self.collection.aggregate.return_value = [{
            "totals": [{"_id": None, "total_trips": 5, "scouting_trips": 2,
                        "total_fish_caught": 19, "largest_fish_weight_lb": 7.5}],
            "user_role_counts": [{"_id": "captain", "count": 2}],
            "team_role_counts": [{"_id": "shooter", "count": 8}],
            "fish_counts": [{"_id": {"fish_id": "fish-1", "name": "Carp"}, "count": 19}],
            "water_type": [{"_id": 1, "count": 5}],
        }]
        data = self.client.get(self.base + "/summary").json()["data"]
        self.assertEqual(data["total_trips"], 5)
        self.assertEqual(data["scouting_trips"], 2)
        self.assertEqual(data["total_fish_caught"], 19)
        self.assertEqual(data["largest_fish_weight_lb"], 7.5)
        self.assertEqual(data["user_role_counts"]["captain"], 2)
        self.assertEqual(data["user_role_counts"]["guest"], 0)
        self.assertEqual(data["team_role_counts"]["shooter"], 8)
        self.assertEqual(data["fish_counts"][0]["count"], 19)
        self.assertEqual(data["breakdowns"]["water_type"], [{"value": 1, "count": 5}])

    def test_no_trips_returns_zero_summary_and_empty_list(self):
        data = self.client.get(self.base).json()["data"]
        self.assertEqual(data["total"], 0)
        self.assertEqual(data["data"], [])
        self.collection.aggregate.return_value = [{}]
        summary = self.client.get(self.base + "/summary").json()["data"]
        self.assertEqual(summary["total_trips"], 0)
        self.assertEqual(summary["total_fish_caught"], 0)
        self.assertEqual(summary["fish_counts"], [])
        self.assertTrue(all(count == 0 for count in summary["user_role_counts"].values()))

    def test_openapi_exposes_query_filters_without_request_body(self):
        schema = self.client.get("/openapi.json").json()
        for path in ("/users/{user_id}/trip-details", "/users/{user_id}/trip-details/summary"):
            operation = schema["paths"][path]["get"]
            self.assertNotIn("requestBody", operation)
            params = {param["name"]: param for param in operation["parameters"]}
            self.assertEqual(params["user_id"]["in"], "path")
            self.assertEqual(params["date"]["in"], "query")
            self.assertEqual(params["scope"]["schema"]["default"], "all")


if __name__ == "__main__":
    unittest.main()
