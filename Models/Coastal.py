# =======================================================
# Coastal states and their areas.
# =======================================================

from pydantic import BaseModel, Field, model_validator
from typing import Optional
from datetime import datetime, timezone
import json
from uuid import uuid4


class AreaModel(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()), min_length=1, pattern=r"\S")
    name: Optional[str] = None  # Example: "North Shore Weed Bed"
    water_body: Optional[str] = None


# =============================================
# CREATE COASTAL MODEL
# =============================================
class CostalModel(BaseModel):
    state: Optional[str] = None  # Example: "North Shore Weed Bed"
    area: Optional[list[AreaModel]] = None  # Example: "North Shore Weed Bed"
    # GPS coordinates
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)  # Example: 37.2095
    longitude: Optional[float] = Field(
        default=None, ge=-180, le=180
    )  # Example: -93.2930
    status: Optional[int] = Field(default=1)
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

    @model_validator(mode="after")
    def validate_area_ids(self):
        if self.area is not None:
            ids = [area.id for area in self.area]
            if len(ids) != len(set(ids)):
                raise ValueError("Area IDs must be unique within a coastal record")
        return self


# =============================================
# UPDATE COASTAL MODEL
# =============================================
class CoastalUpdateModel(BaseModel):
    state: Optional[str] = None  # Example: "North Shore Weed Bed"
    area: Optional[list[AreaModel]] = None  # Example: "North Shore Weed Bed"
    # GPS coordinates
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)  # Example: 37.2095
    longitude: Optional[float] = Field(
        default=None, ge=-180, le=180
    )  # Example: -93.2930
    status: Optional[int] = Field(default=1)
    deleted_at: Optional[datetime] = None
    deleted_by: Optional[str] = None
    updated_at: Optional[datetime] = None

    # Convert JSON string to dictionary if needed
    @model_validator(mode="before")
    @classmethod
    def validate_to_json(cls, value):
        if isinstance(value, str):
            return json.loads(value)
        return value

    @model_validator(mode="after")
    def validate_area_ids(self):
        if self.area is not None:
            ids = [area.id for area in self.area]
            if len(ids) != len(set(ids)):
                raise ValueError("Area IDs must be unique within a coastal record")
        return self


# Preserve the original model name for existing imports.
CoastalModel = CostalModel
