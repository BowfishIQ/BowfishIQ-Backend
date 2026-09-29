from pathlib import Path

import firebase_admin
from firebase_admin import credentials, messaging
from bson import ObjectId

from db import db

# Resolve the key path relative to the project root so it works regardless of CWD
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CRED_PATH = (
    PROJECT_ROOT
    / "uploads"
    / "pushnotification-test-a9548-firebase-adminsdk-fbsvc-61c305557f.json"
)

# Initialize firebase only once (Routes/pushNotification.py may also initialize it)
if not firebase_admin._apps:
    cred = credentials.Certificate(str(CRED_PATH))
    firebase_admin.initialize_app(cred)


def send_push_to_token(token, title, body, data=None):
    """
    Send a push notification to a single FCM device token.
    Never raises - push failures must not break existing functionality.
    """
    try:
        if not token:
            return None
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data={k: str(v) for k, v in (data or {}).items()},
            token=token,
        )
        return messaging.send(message)
    except Exception as e:
        print(f"Push notification failed: {e}")
        return None


def send_push_to_user(user_id, title, body, data=None):
    """
    Look up the user's stored firebase_token and send a push notification.
    Never raises - push failures must not break existing functionality.
    """
    try:
        if not user_id:
            return None
        user = db["user"].find_one({"_id": ObjectId(str(user_id))})
        if not user:
            return None
        return send_push_to_token(user.get("firebase_token"), title, body, data)
    except Exception as e:
        print(f"Push notification failed: {e}")
        return None
