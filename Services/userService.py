import random
from datetime import datetime, timedelta, timezone
from typing import Annotated

from bson import ObjectId
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from config import ACCESS_TOKEN_EXPIRE_MINUTES, APP_NAME, JWT_ALGORITHM, JWT_SECRET_KEY
from db import db
from .common import paginate
from .smtpService import send_email


collection = db["user"]
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/get-token")


def check_email_exist(email: str):
    return collection.find_one({"email": email.strip().lower()})


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=15)
    )
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def user_login_response(request, user, main_login_key, message="Login successful"):
    first_name = user.get("first_name")
    last_name = user.get("last_name")
    full_name = " ".join(part for part in (first_name, last_name) if part).strip()
    profile_image = user.get("profile_image")

    return {
        "message": message,
        "access_token": create_access_token(
            data={"sub": main_login_key},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        ),
        "token_type": "bearer",
        "_id": str(user["_id"]),
        "email": user.get("email"),
        "name": user.get("name") or full_name or None,
        "first_name": first_name,
        "last_name": last_name,
        "profile_image": (
            f"{str(request.base_url).rstrip('/')}/uploads/users/{profile_image}"
            if profile_image
            else None
        ),
        "user_role": user.get("user_role"),
        "verification_status": user.get("verification_status"),
        "status": "success",
    }


def create(request, user_data):
    try:
        data = user_data.model_dump()
        email = (data.get("email") or "").strip().lower()
        google_id = (data.get("google_id") or "").strip()
        apple_id = (data.get("apple_id") or "").strip()
        password = data.get("password") or ""
        login_type = data.pop("login_type", None)

        if not email:
            return {"message": "Email is required", "status": "error"}

        if login_type is None:
            if google_id:
                login_type = 1
            elif apple_id:
                login_type = 3
            elif password:
                login_type = 2
            else:
                return {
                    "message": "Google ID, Apple ID or password is required",
                    "status": "error",
                }

        if login_type in (1, 3):
            provider = "Google" if login_type == 1 else "Apple"
            id_field = "google_id" if login_type == 1 else "apple_id"
            provider_id = google_id if login_type == 1 else apple_id
            if not provider_id:
                return {"message": f"{provider} ID is required", "status": "error"}

            existing_user = collection.find_one({id_field: provider_id})
            if existing_user and existing_user.get("email", "").lower() != email:
                return {
                    "message": f"{provider} ID is already used by another user",
                    "status": "error",
                }
            if existing_user is None:
                existing_user = check_email_exist(email)

            if existing_user:
                stored_provider_id = existing_user.get(id_field)
                if stored_provider_id and stored_provider_id != provider_id:
                    return {
                        "message": f"Email is linked with a different {provider} ID",
                        "status": "error",
                    }

                updates = {"verification_status": 1, "login_type": login_type}
                if not stored_provider_id:
                    updates[id_field] = provider_id
                for field in ("name", "first_name", "last_name"):
                    if data.get(field) is not None:
                        updates[field] = data[field]
                collection.update_one(
                    {"_id": existing_user["_id"]}, {"$set": updates}
                )
                existing_user.update(updates)
                return user_login_response(request, existing_user, existing_user["email"])

            data["google_id"] = google_id if login_type == 1 else None
            data["apple_id"] = apple_id if login_type == 3 else None
            data["password"] = None
        elif login_type == 2:
            if not password:
                return {"message": "Password is required", "status": "error"}
            if check_email_exist(email):
                return {"message": "Email already exists", "status": "error"}
            data["google_id"] = None
            data["apple_id"] = None
            data["password"] = pwd_context.hash(password)
        else:
            return {"message": "Invalid login type", "status": "error"}

        data.update(
            {"email": email, "login_type": login_type, "verification_status": 1}
        )
        result = collection.insert_one(data)
        data["_id"] = result.inserted_id
        return user_login_response(
            request, data, email, "Registration and login successful"
        )
    except Exception as exc:
        return {"message": str(exc), "status": "error"}


def _login_otp_email(email: str, otp: int) -> str:
    year = datetime.now().year
    return f"""
    <!DOCTYPE html>
    <html lang="en">
      <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Login OTP - {APP_NAME}</title>
      </head>
      <body style="font-family:Arial,sans-serif;background:#f4f4f4;padding:24px;">
        <div style="max-width:600px;margin:auto;background:#fff;border-radius:8px;overflow:hidden;">
          <div style="background:#4CAF50;padding:20px;text-align:center;color:#fff;font-size:24px;font-weight:bold;">Login Verification</div>
          <div style="padding:30px;color:#333;line-height:1.6;">
            <p>Hi <strong>{email}</strong>,</p>
            <p>We received a request to log in to your <strong>{APP_NAME}</strong> account.</p>
            <div style="padding:20px;margin:25px 0;text-align:center;background:#f8f9fa;border:1px dashed #dee2e6;border-radius:8px;">
              <div style="font-size:36px;font-weight:bold;letter-spacing:8px;color:#4CAF50;">{otp}</div>
              <p style="color:#dc3545;font-size:14px;font-weight:bold;">This OTP will expire in 5 minutes</p>
            </div>
            <p><strong>Security notice:</strong> Do not share this OTP. {APP_NAME} will never ask you for it.</p>
            <p>If you did not attempt to log in, you can ignore this email.</p>
          </div>
          <div style="background:#f4f4f4;padding:15px;text-align:center;font-size:12px;color:#777;">© {year} {APP_NAME}. All rights reserved.</div>
        </div>
      </body>
    </html>
    """


def login(
    request,
    email=None,
    firebase_token=None,
    login_type=None,
    google_id=None,
    password=None,
    apple_id=None,
):
    try:
        email = (email or "").strip().lower()
        if not email:
            return {"message": "Email is required", "status": "error"}

        user = check_email_exist(email)
        if not user:
            return {"message": "User does not exist", "status": "error"}
        if user.get("verification_status") != 1:
            return {"message": "User not verified", "status": "error"}

        if login_type is None:
            if google_id:
                login_type = 1
            elif apple_id:
                login_type = 3
            elif password:
                login_type = 2

        if login_type == 1:
            google_id = (google_id or "").strip()
            if not google_id:
                return {"message": "Google ID is required", "status": "error"}
            if user.get("google_id") != google_id:
                return {"message": "Invalid Google credentials", "status": "error"}
        elif login_type == 3:
            apple_id = (apple_id or "").strip()
            if not apple_id:
                return {"message": "Apple ID is required", "status": "error"}
            if user.get("apple_id") != apple_id:
                return {"message": "Invalid Apple credentials", "status": "error"}
        elif login_type == 2:
            stored_password = user.get("password")
            if not password:
                return {"message": "Password is required", "status": "error"}
            if not stored_password or not pwd_context.verify(password, stored_password):
                return {"message": "Invalid email or password", "status": "error"}
        elif login_type is None:
            login_otp = random.randint(100000, 999999)
            updates = {
                "login_otp": login_otp,
                "login_otp_expiry": datetime.now(timezone.utc) + timedelta(minutes=5),
            }
            if firebase_token:
                updates["firebase_token"] = firebase_token
            collection.update_one({"_id": user["_id"]}, {"$set": updates})
            result = send_email(
                [email], f"Login OTP - {APP_NAME}", _login_otp_email(email, login_otp)
            )
            if result["status"] == "success":
                return {"message": "Login OTP sent to email", "status": "success"}
            return {"message": result["message"], "status": "error"}
        else:
            return {"message": "Invalid login type", "status": "error"}

        if firebase_token:
            collection.update_one(
                {"_id": user["_id"]}, {"$set": {"firebase_token": firebase_token}}
            )
        return user_login_response(request, user, email)
    except Exception as exc:
        return {"message": str(exc), "status": "error"}


def admin_login(request, email, password: str):
    try:
        email = email.strip().lower()
        user = check_email_exist(email)
        if not user or not user.get("password"):
            return {"message": "Invalid user credentials", "status": "error"}
        if not pwd_context.verify(password, user["password"]):
            return {"message": "Password does not match", "status": "error"}
        return user_login_response(request, user, email)
    except Exception as exc:
        return {"message": str(exc), "status": "error"}


def _user_projection():
    return {
        "_id": {"$toString": "$_id"},
        "name": 1,
        "first_name": 1,
        "last_name": 1,
        "email": 1,
        "google_id": 1,
        "apple_id": 1,
        "profile_image": 1,
        "description": 1,
        "gender": 1,
        "firebase_token": 1,
        "user_role": 1,
        "verification_status": 1,
        "payment_status": 1,
        "status": 1,
        "deleted_at": 1,
        "created_at": 1,
        "created_by": 1,
        "updated_at": 1,
        "updated_by": 1,
    }


def build_user_pipeline(
    role=None,
    user_id=None,
    status=None,
    verification_status=None,
    search_query=None,
):
    match_stage = {
        "deleted_at": {"$in": ["", None]},
        "user_role": {"$ne": 1},
    }
    if role is not None:
        match_stage["user_role"] = role
    if user_id and ObjectId.is_valid(user_id):
        match_stage["_id"] = ObjectId(user_id)
    if status is not None:
        match_stage["status"] = status
    if verification_status is not None:
        match_stage["verification_status"] = verification_status

    pipeline = [{"$match": match_stage}]
    if search_query:
        fields = ("name", "first_name", "last_name", "email")
        conditions = [
            {field: {"$regex": search_query, "$options": "i"}} for field in fields
        ]
        if ObjectId.is_valid(search_query):
            conditions.append({"_id": ObjectId(search_query)})
        pipeline.append({"$match": {"$or": conditions}})

    pipeline.extend(
        [{"$sort": {"created_at": -1}}, {"$project": _user_projection()}]
    )
    return pipeline


def get_all(
    page,
    limit,
    role=None,
    user_id=None,
    status=None,
    verification_status=None,
    search_query=None,
):
    try:
        pipeline = build_user_pipeline(
            role, user_id, status, verification_status, search_query
        )
        return {"data": paginate(collection, pipeline, page, limit), "status": "success"}
    except Exception as exc:
        return {"message": str(exc), "status": "error"}


def get_user_by_id(request, user_id):
    try:
        if not ObjectId.is_valid(user_id):
            return {"message": "Invalid user id", "status": "error"}
        result = list(
            collection.aggregate(
                [
                    {
                        "$match": {
                            "_id": ObjectId(user_id),
                            "deleted_at": {"$in": ["", None]},
                        }
                    },
                    {"$project": _user_projection()},
                ]
            )
        )
        if not result:
            return {"message": "User not found", "data": None, "status": "error"}
        return {"data": result[0], "status": "success"}
    except Exception as exc:
        return {"message": str(exc), "status": "error"}


def update(user_data, user_id):
    try:
        if not ObjectId.is_valid(user_id):
            return {"message": "Invalid user id", "status": "error"}
        object_id = ObjectId(user_id)
        if not collection.find_one({"_id": object_id}):
            return {"message": "User not found", "status": "error"}

        data = user_data.model_dump(exclude_unset=True)
        if "email" in data:
            email = (data.get("email") or "").strip().lower()
            if not email:
                return {"message": "Email cannot be empty", "status": "error"}
            if collection.find_one({"email": email, "_id": {"$ne": object_id}}):
                return {
                    "message": "Email is already used by another user",
                    "status": "error",
                }
            data["email"] = email

        if "google_id" in data:
            google_id = (data.get("google_id") or "").strip()
            if not google_id:
                return {"message": "Google ID cannot be empty", "status": "error"}
            if collection.find_one(
                {"google_id": google_id, "_id": {"$ne": object_id}}
            ):
                return {
                    "message": "Google ID is already used by another user",
                    "status": "error",
                }
            data["google_id"] = google_id

        data["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        collection.update_one({"_id": object_id}, {"$set": data})
        return {"message": "User updated successfully", "status": "success"}
    except Exception as exc:
        return {"message": str(exc), "status": "error"}


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        email = payload.get("sub")
        if not email:
            return {"message": "Invalid token", "status": "error"}
        user = check_email_exist(email)
        if user is None:
            return {"message": "User not found", "status": "error"}
        return user
    except JWTError as exc:
        return {"message": str(exc), "status": "error"}
