from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class Emotion(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    HESITANT = "hesitant"
    FRUSTRATED = "frustrated"
    NEGATIVE = "negative"


class IntentSignal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    interest_score: float = Field(ge=0.0, le=1.0)
    purchase_probability: float = Field(ge=0.0, le=1.0)
    urgency: float = Field(ge=0.0, le=1.0)
    budget_alignment: float = Field(ge=0.0, le=1.0)
    product_fit: float = Field(ge=0.0, le=1.0)
    objection_level: float = Field(ge=0.0, le=1.0)
    engagement_level: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)


class EmotionSignal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    emotion: Emotion
    confidence: float = Field(ge=0.0, le=1.0)