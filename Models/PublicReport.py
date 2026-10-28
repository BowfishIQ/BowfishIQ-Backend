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
class PublicReportModel(BaseModel):
    name: Optional[str] = None  # Example: "North Shore Weed Bed"

    # Address details
    country: Optional[str] = None  # Example: "United States"
    state: Optional[str] = None  # Example: "Missouri"
    city: Optional[str] = None  # Example: "Springfield"
    zip_code: Optional[str] = None  # Example: "65801"

    # GPS coordinates
    latitude: Optional[float] = Field(ge=-90, le=90)  # Example: 37.2089 (required)
    longitude: Optional[float] = Field(ge=-180, le=180)  # Example: -93.2923 (required)

    report_date_time: Optional[str] = None
    water_clarity: Optional[str] = None  # Example: "clear", "fair", "stained", "muddy"
    water_level: Optional[str] = None  # Example: "high", "normal", "low", "flooded"

    temperature: Optional[float] = None  # Example: 75.0 (degrees Fahrenheit)
    fish_seen: Optional[int] = None  # Example: 5
    fish_shot: Optional[int] = None  # Example: 3

    main_species_seen: Optional[str] = None  # Example: "Carp", "buffalo"
    ramp_condition: Optional[str] = None  # Example: "good", "usable", "poor", "closed"

    notes: Optional[str] = None

    images: Optional[list[str]] = Field(
        default_factory=list
    )  # Example: ["image1.jpg", "image2.jpg"]

    submit_public: Optional[bool] = None  # Example: True, False
    post_anonymous: Optional[bool] = None  # Example: True, False

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
# UPDATE DROP PIN MODEL
# =============================================
class PublicReportUpdateModel(BaseModel):

    name: Optional[str] = None  # Example: "North Shore Weed Bed"

    # Address details
    country: Optional[str] = None  # Example: "United States"
    state: Optional[str] = None  # Example: "Missouri"
    city: Optional[str] = None  # Example: "Springfield"
    zip_code: Optional[str] = None  # Example: "65801"

    # GPS coordinates
    latitude: Optional[float] = Field(ge=-90, le=90)  # Example: 37.2089 (required)
    longitude: Optional[float] = Field(ge=-180, le=180)  # Example: -93.2923 (required)

    report_date_time: Optional[str] = None
    water_clarity: Optional[str] = None  # Example: "clear", "fair", "stained", "muddy"
    water_level: Optional[str] = None  # Example: "high", "normal", "low", "flooded"

    temperature: Optional[float] = None  # Example: 75.0 (degrees Fahrenheit)
    fish_seen: Optional[int] = None  # Example: 5
    fish_shot: Optional[int] = None  # Example: 3

    main_species_ssen: Optional[str] = None  # Example: "Carp", "buffalo"
    ramp_condition: Optional[str] = None  # Example: "good", "usable", "poor", "closed"

    notes: Optional[str] = None

    images: Optional[list[str]] = Field(
        default_factory=list
    )  # Example: ["image1.jpg", "image2.jpg"]

    submit_public: Optional[bool] = None  # Example: True, False
    post_anonymous: Optional[bool] = None  # Example: True, False

    # Convert JSON string to dictionary if needed
    @model_validator(mode="before")
    @classmethod
    def validate_to_json(cls, value):
        if isinstance(value, str):
            return json.loads(value)
        return value
