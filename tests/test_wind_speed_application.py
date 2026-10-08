import unittest
from unittest.mock import MagicMock, patch

import requests
from fastapi.testclient import TestClient

import main
from Services import locationService


class WindSpeedApplicationTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(main.app)
        self.coordinates = {"latitude": 20.3049, "longitude": 85.9079}

    @patch.object(locationService.requests, "get")
    def test_coordinates_only_return_current_wind_with_defaults(self, get):
        response = MagicMock()
        response.json.return_value = {
            "current": {
                "wind_speed_10m": 0,
                "wind_direction_10m": 180,
                "time": "2026-10-02T12:00",
            },
            "current_units": {"wind_speed_10m": "mp/h"},
            "timezone": "Asia/Kolkata",
        }
        get.return_value = response

        result = self.client.get("/get_wind_speed/", params=self.coordinates)

        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["status"], "success")
        self.assertEqual(result.json()["data"]["wind_speed"], 0)
        self.assertEqual(result.json()["data"]["wind_speed_unit"], "mp/h")
        self.assertEqual(result.json()["data"]["wind_direction"], "S")
        get.assert_called_once_with(
            "https://api.open-meteo.com/v1/forecast",
            params={
                **self.coordinates,
                "current": "wind_speed_10m,wind_direction_10m",
                "wind_speed_unit": "mph",
                "timezone": "auto",
            },
            timeout=10,
        )
        response.raise_for_status.assert_called_once()

    @patch.object(locationService.requests, "get")
    def test_wind_direction_uses_compass_labels(self, get):
        for degrees, label in (
            (0, "N"), (45, "NE"), (90, "E"), (135, "SE"),
            (180, "S"), (225, "SW"), (270, "W"), (315, "NW"),
            (360, "N"), (22.49, "N"), (22.5, "NE"),
            (337.49, "NW"), (337.5, "N"), (None, None),
        ):
            with self.subTest(degrees=degrees):
                get.return_value.json.return_value = {
                    "current": {"wind_speed_10m": 5, "wind_direction_10m": degrees},
                    "current_units": {"wind_speed_10m": "mp/h"},
                }
                result = self.client.get("/get_wind_speed/", params=self.coordinates)
                self.assertEqual(result.json()["status"], "success")
                self.assertEqual(result.json()["data"]["wind_direction"], label)

    @patch.object(locationService, "get_wind_speed")
    def test_optional_settings_are_forwarded(self, service):
        service.return_value = {"status": "success"}
        result = self.client.get(
            "/get_wind_speed/",
            params={**self.coordinates, "wind_speed_unit": "kn", "timezone": "GMT"},
        )
        self.assertEqual(result.status_code, 200)
        service.assert_called_once_with(20.3049, 85.9079, "kn", "GMT")

    @patch.object(locationService.requests, "get")
    def test_invalid_or_missing_coordinates_and_units_are_rejected(self, get):
        for params in (
            {},
            {"latitude": 20},
            {"longitude": 85},
            {**self.coordinates, "latitude": 91},
            {**self.coordinates, "longitude": -181},
            {**self.coordinates, "latitude": "nan"},
            {**self.coordinates, "longitude": "invalid"},
            {**self.coordinates, "wind_speed_unit": "invalid"},
        ):
            with self.subTest(params=params):
                result = self.client.get("/get_wind_speed/", params=params)
                self.assertEqual(result.status_code, 422)
        get.assert_not_called()

    @patch.object(locationService.requests, "get")
    def test_upstream_failures_return_errors(self, get):
        for error in (requests.Timeout(), requests.ConnectionError(), requests.HTTPError()):
            with self.subTest(error=type(error).__name__):
                get.side_effect = error
                result = self.client.get("/get_wind_speed/", params=self.coordinates)
                self.assertEqual(result.json()["status"], "error")

    @patch.object(locationService.requests, "get")
    def test_invalid_or_missing_weather_data_returns_error(self, get):
        for payload in ({}, {"current": None}, {"current": {"wind_speed_10m": None}}):
            with self.subTest(payload=payload):
                get.return_value.json.return_value = payload
                result = self.client.get("/get_wind_speed/", params=self.coordinates)
                self.assertEqual(result.json()["status"], "error")
        get.return_value.json.side_effect = ValueError("Invalid JSON")
        result = self.client.get("/get_wind_speed/", params=self.coordinates)
        self.assertEqual(result.json()["status"], "error")


if __name__ == "__main__":
    unittest.main()
