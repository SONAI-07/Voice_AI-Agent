from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class InsightClassification(str, Enum):
    STRONG = "strong"
    NEUTRAL = "neutral"
    NOT_INTERESTED = "not_interested"


class CallInsightData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    classification: InsightClassification

    purchase_probability: float = Field(
        ge=0.0,
        le=1.0,
    )

    interest_score: float = Field(
        ge=0.0,
        le=1.0,
    )

    summary: str = Field(
        min_length=1,
        max_length=5000,
    )

    important_details: dict[str, str] = Field(
        default_factory=dict,
    )