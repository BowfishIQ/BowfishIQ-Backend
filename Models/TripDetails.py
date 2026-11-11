from pydantic import BaseModel, Field, model_validator
from typing import Literal, Optional
from datetime import datetime
import json


class CrewDetailsModel(BaseModel):
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    user_role: Optional[list[str]] = None  # 1=Captain, 2=shooter, 3=Spotter, 4=Guest, 5=Other
    status: Optional[int] = Field(default=1)  # 0- deactivate, 1- activate, 2- Blocked

    @model_validator(mode="before")
    @classmethod
    def validate_to_json(cls, value):
        if isinstance(value, str):
            return json.loads(value)
        return value


class FishShotDetailsModel(BaseModel):
    fish_id: Optional[str] = None
    name: Optional[str] = None
    count: Optional[int] = None
    largest_fish: Optional[float] = Field(default=None)  # in LB
    largest_fish_length: Optional[float] = Field(default=None)  # in inches
    status: Optional[int] = Field(default=1)  # 0- deactivate, 1- activate, 2- Blocked

    @model_validator(mode="before")
    @classmethod
    def validate_to_json(cls, value):
        if isinstance(value, str):
            return json.loads(value)
        return value


class TeamDetailsModel(BaseModel):
    name: Optional[str] = None
    role: Optional[list[str]] = None  # 1=Captain, 2=shooter, 3=Spotter, 4=Guest, 5=Other
    shot_count: Optional[int] = None
    status: Optional[int] = Field(default=1)  # 0- deactivate, 1- activate, 2- Blocked

    @model_validator(mode="before")
    @classmethod
    def validate_to_json(cls, value):
        if isinstance(value, str):
            return json.loads(value)
        return value


class TripDetailsModel(BaseModel):
    user_id: Optional[str] = None
    crew_details: Optional[list[CrewDetailsModel]] = None

    trip_type: Optional[int] = Field(default=None)  # 1- regular trip, 2- scouting trip
    water_type: Optional[int] = Field(
        default=None
    )  # 1=Lake / Reservoir, 2=River / Creek, 3=  Pond / Small Water, 4=Coastal (state wise filter with multi select)
    water_salinity: Optional[int] = Field(
        default=None
    )  # 1=Freshwater, 2=Brackish, 3=Saltwater
    lake_locations: Optional[list[str]] = (
        None  # this one connected to maplocation collection _id
    )

    lunch_ramp: Optional[str] = (
        None  # 1=Bucksaw Resort and Marina, 2=Bucksaw, 3=Sterett Creek
    )
    area_fished: Optional[str] = None

    date: Optional[str] = None  # dd-mm-yyyy
    start_time: Optional[str] = None  # hh:mm:ss
    end_time: Optional[str] = None  # hh:mm:ss

    fish_shot_details: Optional[list[FishShotDetailsModel]] = None
    team_details: Optional[list[TeamDetailsModel]] = None

    fish_see_not_shot_count: Optional[int] = Field(default=None)

    water_temp: Optional[float] = Field(default=None)  # in Fahrenheit
    water_clarity: Optional[int] = Field(
        default=None
    )  # 1=Clear, 2=fair, 3=stained, 4=muddy
    water_movement: Optional[int] = Field(default=None)  # 1=Still, 2=light, 3=Moderate
    wind: Optional[int] = Field(default=None)  # 1=Calm, 2=Light, 3=Moderate, 4=Strong
    wind_speed: Optional[float] = Field(default=None)  # in mph
    wind_direction: Optional[int] = Field(
        default=None
    )  # 1=N, 2=NE, 3=E, 4=SE, 5=S, 6=SW, 7=W, 8=NW

    water_level: Optional[int] = Field(default=None)  # 1=Low, 2=Normal, 3=High
    water_base: Optional[int] = Field(default=None)  # 1=below, 2=above
    water_depth: Optional[float] = Field(default=None)  # in feet

    fish_location: Optional[list[str]] = (
        None  #  1 = Shoreline, 2 = Mud flats, 3 = Grass, 4 = Bushes, 5 = Riprap, 6 = Creek channel, 7 = Main lake, 8 = Suspended, 9 = Flooded timber
    )

    trip_outcome: Optional[str] = None
    trip_lessons: Optional[str] = None
    trip_notes: Optional[str] = None

    images: Optional[list[str]] = None

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


class TripDetailsUpdateModel(TripDetailsModel):
    """Optional trip fields for partial updates, without creation defaults."""

    status: Optional[int] = None
    created_at: Optional[str] = None
    created_date: Optional[str] = None
    created_time: Optional[str] = None


class UserTripFilters(BaseModel):
    """Shared query parameters for user trip lists and summaries."""

    date: Optional[str] = Field(default=None, description="Exact trip date: DD-MM-YYYY or YYYY-MM-DD")
    start_date: Optional[str] = Field(default=None, description="Inclusive first trip date")
    end_date: Optional[str] = Field(default=None, description="Inclusive last trip date")
    trip_id: Optional[str] = None
    scope: Literal["all", "owner", "crew"] = "all"
    trip_type: Optional[int] = Field(default=None, ge=1, le=2)
    status: Optional[int] = Field(default=None, ge=0, le=2)
    water_type: Optional[int] = Field(default=None, ge=1, le=4)
    water_salinity: Optional[int] = Field(default=None, ge=1, le=3)
    lake_location_id: Optional[str] = None
