from app.agent.action import BusinessAction
from app.agent.classification import CustomerClassification


def determine_post_call_action(
        classification: CustomerClassification,
        *,
        whatsapp_already_sent: bool,
) -> BusinessAction | None:

    if classification == CustomerClassification.STRONG:

        if not whatsapp_already_sent:
            return BusinessAction.SEND_WHATSAPP_BROCHURE

        return None

    if classification == CustomerClassification.NEUTRAL:
        return BusinessAction.SCHEDULE_FOLLOW_UP

    if classification == CustomerClassification.NOT_INTERESTED:
        return BusinessAction.SEND_EMAIL_BROCHURE

    return None