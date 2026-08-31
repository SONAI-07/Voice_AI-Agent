from enum import Enum

from pydantic import BaseModel, ConfigDict

from app.agent.classification import CustomerClassification
from app.agent.live_policy import should_send_whatsapp_now
from app.agent.state import AgentState


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
        state: AgentState,
) -> ActionDecision:

    classification = state["classification"]

    if classification is None:
        raise ValueError(
            "Classification is missing from state"
        )

    # The ONLY action permitted during the live call.
    #
    # It requires:
    #   1. sustained high intent
    #   2. explicit positive buying signal
    #   3. WhatsApp has not already been triggered
    if should_send_whatsapp_now(state):
        return ActionDecision(
            action=BusinessAction.SEND_WHATSAPP_BROCHURE,
            classification=classification.classification,
        )

    # Every other business action is deferred until
    # the call has disconnected.
    return ActionDecision(
        action=BusinessAction.CONTINUE_CONVERSATION,
        classification=classification.classification,
    )