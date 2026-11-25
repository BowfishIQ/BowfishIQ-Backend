"""Structured AI narrative and the public trip analysis response."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AnalysisModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AnalysisCard(AnalysisModel):
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=1200)


class TripAnalysisNarrative(AnalysisModel):
    trip_iq_score: int | None = Field(ge=0, le=100)
    score_explanation: str = Field(min_length=1, max_length=1200)
    summary: str = Field(min_length=1, max_length=3000)
    what_went_well: list[AnalysisCard] = Field(max_length=5)
    what_limited_success: list[AnalysisCard] = Field(max_length=5)
    ai_recommendations: list[AnalysisCard] = Field(max_length=5)
    data_limitations: list[str] = Field(max_length=10)


class AnalysisBaseline(AnalysisModel):
    trip_count: int
    average_fish: float | None
    average_fish_per_shooter: float | None
    trips_with_shooter_count: int


class TripComparison(AnalysisModel):
    trip_fish: float
    trip_fish_per_shooter: float | None
    personal: AnalysisBaseline
    community: AnalysisBaseline
    category: Literal["inland", "coastal"]
    scope: str


class AnalysisMetrics(AnalysisModel):
    total_fish: float
    shooter_count: int
    fish_per_shooter: float | None
    fish_per_hour: float | None
    fish_per_shooter_per_hour: float | None
    duration_hours: float | None
    fish_seen: float | None
    conversion_rate_percent: float | None
    species_count: int


class TripAnalysisData(TripAnalysisNarrative):
    trip_id: str
    title: Literal["AI Trip Analysis"]
    trip_iq_label: str
    score_max: Literal[100]
    score_source: Literal["AI assessment"]
    metrics: AnalysisMetrics
    trip_comparison: TripComparison
    generated_at: str
    model: str
    source_note: str


class TripAnalysisResponse(AnalysisModel):
    status: Literal["success"]
    data: TripAnalysisData
