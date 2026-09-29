from pydantic import BaseModel, Field, model_validator
from typing import Optional
from datetime import datetime
import json


class UserModel(BaseModel):
    name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    google_id: Optional[str] = None
    password: Optional[str] = None
    login_type: Optional[int] = Field(default=None, ge=1, le=2)

    # profile_image: Optional[str] = None

    # gender: Optional[str] = None
    # firebase_token: Optional[str] = None

    user_role: Optional[int] = Field(
        default=2
    )  # 1- Super Admin, 2- player

    verification_status: Optional[int] = Field(
        default=0
    )  # 0- not verified, 1- verified

    payment_status: Optional[int] = Field(default=0)  # 0- unpaid, 1- paid
    status: Optional[int] = Field(default=1)  # 0- deactivate, 1- activate, 2- Blocked

    deleted_at: Optional[str] = None
    deleted_by: Optional[str] = None
    created_at: Optional[str] = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    created_date: Optional[str] = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d")
    )
    created_time: Optional[str] = Field(
        default_factory=lambda: datetime.now().strftime("%H:%M:%S")
    )
    created_by: Optional[str] = None
    updated_at: Optional[str] = None
    updated_by: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def validate_to_json(cls, value):
        if isinstance(value, str):
            return json.loads(value)
        return value


class UserUpdateModel(BaseModel):
    name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    google_id: Optional[str] = None

    profile_image: Optional[str] = None
    description: Optional[str] = None

    gender: Optional[str] = None
    firebase_token: Optional[str] = None

    user_role: Optional[int] = Field(default=2)  # 1- Super Admin, 2- player

    payment_status: Optional[int] = Field(default=0)

    status: Optional[int] = Field(default=1)  # 0- deactivate, 1- activate, 2- Blocked
    deleted_by: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def validate_to_json(cls, value):
        if isinstance(value, str):
            return json.loads(value)
        return value

class Token(BaseModel):
    access_token: str
    token_type: str
