# =======================================================
# Lake records and optional references to other lake records.
# =======================================================

from pydantic import BaseModel, Field, model_validator
from typing import Optional, Literal
from datetime import datetime, timezone
import json


# =============================================
# CREATE LAKE MODEL
# =============================================
class LakesModel(BaseModel):
    user_id: Optional[str] = None

    name: Optional[str] = None  # Example: "North Shore Weed Bed"

    # Address details
    country: Optional[str] = None  # Example: "United States"
    state: Optional[list[str]] = Field(default=None, max_length=2)
    city: Optional[str] = None  # Example: "Springfield"
    zip_code: Optional[str] = None  # Example: "65801"

    # GPS coordinates
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)  # Example: 37.2095
    longitude: Optional[float] = Field(
        default=None, ge=-180, le=180
    )  # Example: -93.2930

    water_type: Optional[str] = (
        None  # Example: "Lake", "River", "Reservoir", "creek", "other"
    )

    water_data: Optional[str] = None # it should be _id of own LakesModel
    gauge_data: Optional[str] = None

    notes: Optional[str] = None

    status: Literal[0, 1, 2] = 1  # 0 = Inactive, 1 = Active, 2 = Blocked

    deleted_at: Optional[datetime] = None
    deleted_by: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None

    # Convert JSON string to dictionary if needed
    @model_validator(mode="before")
    @classmethod
    def validate_to_json(cls, value):
        if isinstance(value, str):
            return json.loads(value)
        return value


# =============================================
# UPDATE LAKE MODEL
# =============================================
class LakesUpdateModel(BaseModel):

    user_id: Optional[str] = None

    name: Optional[str] = None  # Example: "North Shore Weed Bed"

    # Address details
    country: Optional[str] = None  # Example: "United States"
    state: Optional[list[str]] = Field(default=None, max_length=2)
    city: Optional[str] = None  # Example: "Springfield"
    zip_code: Optional[str] = None  # Example: "65801"

    # GPS coordinates
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)  # Example: 37.2095
    longitude: Optional[float] = Field(
        default=None, ge=-180, le=180
    )  # Example: -93.2930

    water_type: Optional[str] = (
        None  # Example: "Lake", "River", "Reservoir", "creek", "other"
    )

    water_data: Optional[str] = None # it should be _id of own LakesModel
    gauge_data: Optional[str] = None

    notes: Optional[str] = None

    # Convert JSON string to dictionary if needed
    @model_validator(mode="before")
    @classmethod
    def validate_to_json(cls, value):
        if isinstance(value, str):
            return json.loads(value)
        return value
