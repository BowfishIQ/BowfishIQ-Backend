from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


FishFamily = Literal[
    "Buffalo", "Carp", "Gar", "Sucker", "Drum", "Catfish", "Bowfin",
    "Tilapia", "Paddlefish", "Snakehead", "Other",
]
FISH_FAMILIES = (
    "Buffalo", "Carp", "Gar", "Sucker", "Drum", "Catfish", "Bowfin",
    "Tilapia", "Paddlefish", "Snakehead", "Other",
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class FishInventoryRow(StrictModel):
    id: int = Field(ge=1)
    region: str = Field(min_length=1)
    family: FishFamily
    evidence: str = Field(min_length=1)


class FishInventory(StrictModel):
    fish: list[FishInventoryRow]
    total: int = Field(ge=0)
    confidence: int = Field(ge=0, le=100)
    note: str | None


class AuditedFishRow(FishInventoryRow):
    draftId: int | None = Field(ge=1)


class FishGroup(StrictModel):
    family: FishFamily
    count: int = Field(ge=0)


class FishAudit(StrictModel):
    auditedFish: list[AuditedFishRow]
    groups: list[FishGroup]
    finalTotal: int = Field(ge=0)
    confidence: int = Field(ge=0, le=100)
    note: str | None


class FishCountResponse(StrictModel):
    status: Literal["success"]
    data: FishAudit
