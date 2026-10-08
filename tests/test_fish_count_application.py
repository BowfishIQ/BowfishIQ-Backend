from io import BytesIO
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from openai import APITimeoutError
import httpx
from PIL import Image

import main
from Models.FishCount import FishAudit, FishInventory
from Routes import fishCountRoute
from Services import fishCountService


def image_file():
    output = BytesIO()
    Image.new("RGB", (10, 10), "white").save(output, format="PNG")
    return output.getvalue()


def draft_payload():
    return {
        "fish": [{"id": 1, "region": "left", "family": "Carp",
                  "evidence": "visible mouth-corner barbels"}],
        "total": 99, "confidence": 70, "note": None,
    }


def audit_payload():
    return {
        "auditedFish": [
            {"id": 1, "draftId": 1, "region": "left", "family": "Buffalo",
             "evidence": "deep body, humped shoulder, sweeping dorsal"},
            {"id": 2, "draftId": None, "region": "right", "family": "Gar",
             "evidence": "long cylindrical body and extended beak-like snout"},
        ],
        "groups": [{"family": "Carp", "count": 99}],
        "finalTotal": 99, "confidence": 80, "note": "One tail is partly covered.",
    }


def completed(payload):
    return SimpleNamespace(status="completed", output_parsed=payload)


class FishCountApplicationTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(main.app)
        self.key_patch = patch.object(fishCountService, "OPENAI_API_KEY", "test-key")
        self.key_patch.start()
        self.addCleanup(self.key_patch.stop)
        self.sdk_patch = patch.object(fishCountService, "OpenAI")
        self.sdk = self.sdk_patch.start()
        self.addCleanup(self.sdk_patch.stop)
        self.parse = self.sdk.return_value.__enter__.return_value.responses.parse
        self.parse.side_effect = [completed(draft_payload()), completed(audit_payload())]

    def upload(self, content=None):
        return self.client.post("/fish-count/", files={
            "image": ("catch.png", image_file() if content is None else content, "image/png")
        })

    def test_two_pass_pipeline_uses_same_image_and_full_draft(self):
        response = self.upload()
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertEqual(data["finalTotal"], 2)
        self.assertEqual(data["groups"], [
            {"family": "Buffalo", "count": 1}, {"family": "Gar", "count": 1}
        ])
        self.assertEqual(sum(group["count"] for group in data["groups"]), data["finalTotal"])
        self.assertEqual(data["confidence"], 80)
        self.assertEqual(self.parse.call_count, 2)
        first, second = [call.kwargs for call in self.parse.call_args_list]
        self.assertIs(first["text_format"], FishInventory)
        self.assertIs(second["text_format"], FishAudit)
        self.assertEqual(first["input"][0]["content"][1], second["input"][0]["content"][1])
        self.assertTrue(first["input"][0]["content"][1]["image_url"].startswith("data:image/png;base64,"))
        review_text = second["input"][0]["content"][0]["text"]
        self.assertIn('"total":1', review_text)
        self.assertIn("visible mouth-corner barbels", review_text)
        for request in (first, second):
            self.assertFalse(request["store"])
            self.assertIn("GAR VS SUCKER IS A MANDATORY", request["instructions"])
            self.assertIn("CARP VS BUFFALO IS A MANDATORY", request["instructions"])

    def test_no_fish_returns_zero_and_empty_groups(self):
        self.parse.side_effect = [
            completed({"fish": [], "total": 0, "confidence": 95, "note": None}),
            completed({"auditedFish": [], "groups": [], "finalTotal": 0,
                       "confidence": 95, "note": None}),
        ]
        response = self.upload()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["finalTotal"], 0)
        self.assertEqual(response.json()["data"]["groups"], [])

    def test_missing_key_returns_configuration_error_without_ai_calls(self):
        with patch.object(fishCountService, "OPENAI_API_KEY", ""):
            response = self.upload()
        self.assertEqual(response.status_code, 503)
        self.assertIn("OPENAI_API_KEY", response.json()["detail"])
        self.sdk.assert_not_called()

    def test_bad_uploads_do_not_call_ai(self):
        self.assertEqual(self.client.post("/fish-count/").status_code, 422)
        self.assertEqual(self.upload(b"").status_code, 400)
        self.assertEqual(self.upload(b"not an image").status_code, 400)
        with patch.object(fishCountRoute, "MAX_IMAGE_BYTES", 10):
            self.assertEqual(self.upload().status_code, 413)
        output = BytesIO()
        Image.new("RGB", (5, 5)).save(output, format="GIF")
        self.assertEqual(self.upload(output.getvalue()).status_code, 415)
        self.sdk.assert_not_called()

    def test_refused_or_incomplete_inventory_stops_before_review(self):
        for status in ("completed", "incomplete"):
            with self.subTest(status=status):
                self.parse.reset_mock()
                self.parse.side_effect = [SimpleNamespace(status=status, output_parsed=None)]
                self.assertEqual(self.upload().status_code, 502)
                self.assertEqual(self.parse.call_count, 1)

    def test_invalid_review_is_rejected(self):
        for invalid in ("family", "confidence", "duplicate_id", "duplicate_draft", "unknown_draft"):
            with self.subTest(invalid=invalid):
                audit = audit_payload()
                if invalid == "family":
                    audit["auditedFish"][0]["family"] = "Smallmouth Buffalo"
                elif invalid == "confidence":
                    audit["confidence"] = 101
                elif invalid == "duplicate_id":
                    audit["auditedFish"][1]["id"] = 1
                elif invalid == "duplicate_draft":
                    audit["auditedFish"][1]["draftId"] = 1
                else:
                    audit["auditedFish"][1]["draftId"] = 20
                self.parse.side_effect = [completed(draft_payload()), completed(audit)]
                self.assertEqual(self.upload().status_code, 502)

    def test_ai_timeout_returns_gateway_timeout(self):
        self.parse.side_effect = APITimeoutError(request=httpx.Request("POST", "https://api.openai.com/v1/responses"))
        self.assertEqual(self.upload().status_code, 504)


if __name__ == "__main__":
    unittest.main()
