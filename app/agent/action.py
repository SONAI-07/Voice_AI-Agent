from enum import Enum
from pydantic import BaseModel, ConfigDict
from app.agent.classification import CustomerClassification, ClassificationResult


class BusinessAction(str, Enum):
    SEND_WHATSAPP_BROCHURE = "send_whatsapp_brochure"
    CONTINUE_CONVERSATION = "continue_conversation"
    SCHEDULE_FOLLOW_UP = "schedule_follow_up"
    SEND_EMAIL_BROCHURE = "send_email_brochure"
    END_SALES_WORKFLOW = "end_sales_workflow"


class ActionDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: BusinessAction
    classification: CustomerClassification


def determine_business_action(
        classification: ClassificationResult,
) -> ActionDecision:

    if classification.classification == CustomerClassification.STRONG:
        return ActionDecision(
            action=BusinessAction.SEND_WHATSAPP_BROCHURE,
            classification=classification.classification,
        )

    if classification.classification == CustomerClassification.NOT_INTERESTED:
        return ActionDecision(
            action=BusinessAction.SEND_EMAIL_BROCHURE,
            classification=classification.classification,
        )

    return ActionDecision(
        action=BusinessAction.CONTINUE_CONVERSATION,
        classification=classification.classification,
    )