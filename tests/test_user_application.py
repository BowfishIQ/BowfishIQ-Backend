import unittest
from unittest.mock import MagicMock, patch

from jose import jwt

import main
from Models.User import UserModel, UserUpdateModel
from Services import smtpService, userService
from config import APP_NAME, JWT_ALGORITHM, JWT_SECRET_KEY


class UserApplicationTests(unittest.TestCase):
    def test_application_name_and_active_routes(self):
        self.assertEqual(APP_NAME, "bowfishIQ")
        self.assertEqual(main.app.title, APP_NAME)

        paths = {route.path for route in main.app.routes}
        self.assertIn("/users/", paths)
        self.assertIn("/users/login/", paths)
        self.assertIn("/get-token", paths)
        self.assertNotIn("/teams", paths)
        self.assertNotIn("/gameplay", paths)

    def test_user_model_defaults_match_current_roles(self):
        self.assertEqual(UserModel().user_role, 2)
        self.assertEqual(UserUpdateModel().user_role, 2)
        self.assertIsNotNone(UserModel().created_at)

    def test_access_token_has_expiration(self):
        token = userService.create_access_token({"sub": "person@example.com"})
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        self.assertEqual(payload["sub"], "person@example.com")
        self.assertIn("exp", payload)

    def test_login_email_uses_application_name(self):
        body = userService._login_otp_email("person@example.com", 123456)
        self.assertIn(APP_NAME, body)
        self.assertNotIn("KareSpecial", body)

    @patch.object(smtpService.smtplib, "SMTP_SSL")
    def test_smtp_sender_uses_application_name(self, smtp_ssl):
        server = MagicMock()
        smtp_ssl.return_value.__enter__.return_value = server

        with patch.object(smtpService, "SMTP_USERNAME", "sender@example.com"), patch.object(
            smtpService, "SMTP_PASSWORD", "secret"
        ):
            result = smtpService.send_email(
                ["person@example.com"], "Subject", "<p>Body</p>"
            )

        self.assertEqual(result["status"], "success")
        message = server.sendmail.call_args.args[2]
        self.assertIn(f"From: {APP_NAME} <sender@example.com>", message)


if __name__ == "__main__":
    unittest.main()
