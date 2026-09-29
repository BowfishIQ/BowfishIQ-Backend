from pydantic import BaseModel, Field, model_validator
from typing import Optional
from datetime import datetime
import json


class MapLocationModel(BaseModel):
    name: Optional[str] = None

    country: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    zip_code: Optional[str] = None
    latitude: str
    longitude: str

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


class MapLocationUpdateModel(BaseModel):
    name: Optional[str] = None
    
    country: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    zip_code: Optional[str] = None
    latitude: Optional[str] = None
    longitude: Optional[str] = None

    status: Optional[int] = None  # 0- deactivate, 1- activate, 2- Blocked
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
