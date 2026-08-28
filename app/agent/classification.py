from enum import Enum
from pydantic import BaseModel, ConfigDict, Field
from app.agent.signals import EmotionSignal, IntentSignal


class CustomerClassification(str, Enum):
    STRONG = "strong"
    NEUTRAL = "neutral"
    NOT_INTERESTED = "not_interested"


class ClassificationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    classification: CustomerClassification
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str = Field(min_length=1)


def classify_customer(
        intent: IntentSignal,
        emotion: EmotionSignal,
) -> ClassificationResult:
    """
    Deterministic business classification.

    Emotion is deliberately NOT used as the primary determinant
    of purchase classification.
    """

    if intent.confidence < 0.50:
        return ClassificationResult(
            classification=CustomerClassification.NEUTRAL,
            confidence=intent.confidence,
            rationale="Intent confidence is too low for a strong classification.",
        )

    if (
            intent.purchase_probability >= 0.75
            and intent.interest_score >= 0.70
            and intent.product_fit >= 0.60
            and intent.objection_level <= 0.40
    ):
        return ClassificationResult(
            classification=CustomerClassification.STRONG,
            confidence=intent.confidence,
            rationale="Strong purchase probability and interest with acceptable fit and objection levels.",
        )

    if (
            intent.purchase_probability <= 0.20
            and intent.interest_score <= 0.25
            and intent.engagement_level <= 0.40
    ):
        return ClassificationResult(
            classification=CustomerClassification.NOT_INTERESTED,
            confidence=intent.confidence,
            rationale="Low purchase probability, low interest, and low engagement indicate weak buying intent.",
        )

    return ClassificationResult(
        classification=CustomerClassification.NEUTRAL,
        confidence=intent.confidence,
        rationale="Customer intent is neither sufficiently strong nor sufficiently negative.",
    )