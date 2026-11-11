# =======================================================
# this model is for drop pin, save spot and favorite spot
# =======================================================


from pydantic import BaseModel, Field, model_validator
from typing import Optional, Literal
from datetime import datetime, timezone
import json

# Available scouting pin categories
PinType = Literal[
    "weed_bed",  # Underwater area with aquatic vegetation
    "rock_pile",  # Underwater rocks or rocky structures
    "submerged_timber",  # Underwater fallen trees or timber
    "shallow_flat",  # Shallow water area
    "feeder_creek",  # Small creek flowing into a lake or river
    "culvert",  # Water passage under a road or structure
    "shoal",  # Shallow rocky or sandy area
    "other",  # Any other scouting location
]


# =============================================
# CREATE DROP PIN MODEL
# =============================================
class MapLocationDropPinModel(BaseModel):
    user_id: Optional[str] = None

    name: Optional[str] = None  # Example: "North Shore Weed Bed"

    # Address details
    country: Optional[str] = None  # Example: "United States"
    state: Optional[str] = None  # Example: "Missouri"
    city: Optional[str] = None  # Example: "Springfield"
    zip_code: Optional[str] = None  # Example: "65801"

    # GPS coordinates
    latitude: float = Field(ge=-90, le=90)  # Example: 37.2089 (required)
    longitude: float = Field(ge=-180, le=180)  # Example: -93.2923 (required)

    pin_type: PinType = (
        "other"  # Options: boat ramp, praduct area, cove, bank, flat, shallow water, deep water, hazard, other
    )
    water_body_id: Optional[str] = (
        None  # Example: "stockton lake" ID of the lake or river where the pin is dropped
    )
    target_species: list[str] = Field(
        default_factory=list
    )  # Example: ["common_carp", "buffalo", "gar"] Multiple species can be selected
    water_depth_ft: Optional[float] = Field(
        default=None, ge=0
    )  # Example: 4.5 (4.5 feet deep)

    privacy: Optional[Literal["public", "private", "friend-only"]] = (
        None  # Options: public, private, friends-only
    )
    notes: Optional[str] = None

    # Favorite spot status
    is_favorite: bool = False

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
class MapLocationDropPinUpdateModel(BaseModel):

    # Update location name
    name: Optional[str] = None  # Example: "Updated North Shore Spot"

    # Update address details
    country: Optional[str] = None  # Example: "United States"
    state: Optional[str] = None  # Example: "Missouri"
    city: Optional[str] = None  # Example: "Springfield"
    zip_code: Optional[str] = None  # Example: "65801"
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)  # Example: 37.2095
    longitude: Optional[float] = Field(
        default=None, ge=-180, le=180
    )  # Example: -93.2930

    pin_type: PinType = (
        "other"  # Options: boat ramp, praduct area, cove, bank, flat, shallow water, deep water, hazard, other
    )
    water_body_id: Optional[str] = (
        None  # Example: "lake_123" ID of the lake or river where the pin is dropped
    )
    target_species: list[str] = Field(
        default_factory=list
    )  # Example: ["common_carp", "buffalo", "gar"] Multiple species can be selected
    water_depth_ft: Optional[float] = Field(
        default=None, ge=0
    )  # Example: 4.5 (4.5 feet deep)

    privacy: Optional[Literal["public", "private", "friend-only"]] = (
        None  # Options: public, private, friends-only
    )
    notes: Optional[str] = None

    is_favorite: Optional[bool] = None

    # Convert JSON string to dictionary if needed
    @model_validator(mode="before")
    @classmethod
    def validate_to_json(cls, value):
        if isinstance(value, str):
            return json.loads(value)
        return value
