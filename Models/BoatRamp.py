# =======================================================
# this model is for drop pin, save spot and favorite spot
# =======================================================


from pydantic import BaseModel, Field, model_validator
from typing import Optional, Literal
from datetime import datetime, timezone
import json


# =============================================
# CREATE DROP PIN MODEL
# =============================================
class BoatRampModel(BaseModel):
    name: Optional[str] = None  # Example: "North Shore Weed Bed"

    lake_river: Optional[str] = None  # Example: "Lake of the Ozarks"

    # Address details
    country: Optional[str] = None  # Example: "United States"
    state: Optional[str] = None  # Example: "Missouri"
    city: Optional[str] = None  # Example: "Springfield"
    zip_code: Optional[str] = None  # Example: "65801"

    # GPS coordinates
    latitude: Optional[float] = Field(ge=-90, le=90)  # Example: 37.2089 (required)
    longitude: Optional[float] = Field(ge=-180, le=180)  # Example: -93.2923 (required)
    

    ramp_type: Optional[str] = None  # Example: "private", "marina", "public", "unknown"
    parking_type: Optional[str] = None  # Example: "ample", "limited", "none", "unknown"
    condition: Optional[str] = (
        None  # Example: "good", "usable", "poor", "closed", "unknown"
    )
    night_access: Optional[bool] = None  # Example: True, False
    fee: Optional[float] = None  # Example: 5.0 (dollars)
    dock_availability: Optional[bool] = None  # Example: True, False
    bathroom_availability: Optional[bool] = None  # Example: True, False
    notes: Optional[str] = None

    post_anonymous: Optional[bool] = None  # Example: True, False

    status: Literal[0, 1, 2] = 1  # 0 = Inactive, 1 = Active, 2 = Blocked

    user_id: Optional[str] = None

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
# UPDATE DROP PIN MODEL
# =============================================
class BoatRampUpdateModel(BaseModel):

    # Update location name
    name: Optional[str] = None  # Example: "Updated North Shore Spot"
    lake_river: Optional[str] = None

    # Update address details
    country: Optional[str] = None  # Example: "United States"
    state: Optional[str] = None  # Example: "Missouri"
    city: Optional[str] = None  # Example: "Springfield"
    zip_code: Optional[str] = None  # Example: "65801"
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)  # Example: 37.2095
    longitude: Optional[float] = Field(
        default=None, ge=-180, le=180
    )  # Example: -93.2930

    ramp_type: Optional[str] = None  # Example: "private", "marina", "public", "unknown"
    parking_type: Optional[str] = None  # Example: "ample", "limited", "none", "unknown"
    condition: Optional[str] = (
        None  # Example: "good", "usable", "poor", "closed", "unknown"
    )
    night_access: Optional[bool] = None  # Example: True, False
    fee: Optional[float] = None  # Example: 5.0 (dollars)
    dock_availability: Optional[bool] = None  # Example: True, False
    bathroom_availability: Optional[bool] = None  # Example: True, False
    notes: Optional[str] = None

    post_anonymous: Optional[bool] = None  # Example: True, False


    # Convert JSON string to dictionary if needed
    @model_validator(mode="before")
    @classmethod
    def validate_to_json(cls, value):
        if isinstance(value, str):
            return json.loads(value)
        return value
