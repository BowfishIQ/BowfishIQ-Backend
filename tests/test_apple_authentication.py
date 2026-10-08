import unittest
from unittest.mock import MagicMock, patch

from bson import ObjectId
from fastapi import FastAPI
from fastapi.testclient import TestClient
from jose import jwt

from Routes.userRoute import router
from Services import userService
from config import JWT_ALGORITHM, JWT_SECRET_KEY


class AppleAuthenticationTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)
        self.collection = MagicMock()
        self.collection.find_one.return_value = None
        self.collection.insert_one.return_value.inserted_id = ObjectId()
        patcher = patch.object(userService, "collection", self.collection)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.client.close)
        self.user = {
            "_id": ObjectId(),
            "email": "person@example.com",
            "apple_id": "apple-user-123",
            "verification_status": 1,
        }

    def assert_login_success(self, result):
        self.assertEqual(result["status"], "success")
        payload = jwt.decode(
            result["access_token"], JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM]
        )
        self.assertEqual(payload["sub"], "person@example.com")
        self.assertIn("exp", payload)

    def test_register_apple_user_with_explicit_or_inferred_type(self):
        for login_type in (3, None):
            with self.subTest(login_type=login_type):
                result = self.client.post(
                    "/users/",
                    json={
                        "email": " Person@Example.com ",
                        "apple_id": " apple-user-123 ",
                        "login_type": login_type,
                        "first_name": "Person",
                    },
                ).json()
                self.assert_login_success(result)
                data = self.collection.insert_one.call_args.args[0]
                self.assertEqual(data["apple_id"], "apple-user-123")
                self.assertEqual(data["login_type"], 3)
                self.assertEqual(data["verification_status"], 1)
                self.assertIsNone(data["password"])
                self.assertIsNone(data["google_id"])

    def test_registration_requires_apple_id(self):
        result = self.client.post(
            "/users/", json={"email": self.user["email"], "login_type": 3}
        ).json()
        self.assertEqual(result["message"], "Apple ID is required")
        self.collection.insert_one.assert_not_called()

    def test_registration_rejects_apple_id_used_by_another_email(self):
        self.collection.find_one.return_value = self.user
        result = self.client.post(
            "/users/",
            json={"email": "other@example.com", "apple_id": self.user["apple_id"]},
        ).json()
        self.assertEqual(result["message"], "Apple ID is already used by another user")
        self.collection.insert_one.assert_not_called()
        self.collection.update_one.assert_not_called()

    def test_registration_rejects_email_with_a_different_apple_id(self):
        self.collection.find_one.side_effect = [None, self.user]
        result = self.client.post(
            "/users/",
            json={"email": self.user["email"], "apple_id": "different-apple-id"},
        ).json()
        self.assertEqual(result["message"], "Email is linked with a different Apple ID")
        self.collection.update_one.assert_not_called()

    def test_registration_logs_in_existing_apple_user_without_duplicate(self):
        self.collection.find_one.return_value = self.user.copy()
        result = self.client.post(
            "/users/",
            json={"email": self.user["email"], "apple_id": self.user["apple_id"]},
        ).json()
        self.assert_login_success(result)
        self.collection.insert_one.assert_not_called()

    def test_registration_links_apple_id_to_existing_email(self):
        existing = self.user.copy()
        existing.pop("apple_id")
        self.collection.find_one.side_effect = [None, existing]
        result = self.client.post(
            "/users/",
            json={"email": self.user["email"], "apple_id": self.user["apple_id"]},
        ).json()
        self.assert_login_success(result)
        updates = self.collection.update_one.call_args.args[1]["$set"]
        self.assertEqual(updates["apple_id"], self.user["apple_id"])
        self.assertEqual(updates["login_type"], 3)
        self.collection.insert_one.assert_not_called()

    def test_login_accepts_apple_id_and_updates_firebase_token(self):
        self.collection.find_one.return_value = self.user
        for login_type in (3, None):
            with self.subTest(login_type=login_type):
                result = self.client.post(
                    "/users/login/",
                    json={
                        "email": self.user["email"],
                        "apple_id": " apple-user-123 ",
                        "login_type": login_type,
                        "firebase_token": "device-token",
                    },
                ).json()
                self.assert_login_success(result)
                self.collection.update_one.assert_called_with(
                    {"_id": self.user["_id"]},
                    {"$set": {"firebase_token": "device-token"}},
                )

    def test_login_rejects_missing_or_incorrect_apple_id(self):
        self.collection.find_one.return_value = self.user
        for apple_id, message in (
            (None, "Apple ID is required"),
            ("   ", "Apple ID is required"),
            ("wrong-id", "Invalid Apple credentials"),
        ):
            with self.subTest(apple_id=apple_id):
                result = self.client.post(
                    "/users/login/",
                    json={"email": self.user["email"], "apple_id": apple_id, "login_type": 3},
                ).json()
                self.assertEqual(result["status"], "error")
                self.assertEqual(result["message"], message)
                self.assertNotIn("access_token", result)
        self.collection.update_one.assert_not_called()

    def test_google_registration_still_works(self):
        result = self.client.post(
            "/users/",
            json={"email": self.user["email"], "google_id": "google-user-123"},
        ).json()
        self.assert_login_success(result)
        data = self.collection.insert_one.call_args.args[0]
        self.assertEqual(data["google_id"], "google-user-123")
        self.assertEqual(data["login_type"], 1)
        self.assertIsNone(data["apple_id"])


if __name__ == "__main__":
    unittest.main()
