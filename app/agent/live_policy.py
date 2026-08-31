from app.agent.state import AgentState


HIGH_INTENT_THRESHOLD = 0.75
HIGH_INTEREST_THRESHOLD = 0.70
MIN_INTENT_CONFIDENCE = 0.60

REQUIRED_CONSECUTIVE_TURNS = 3


def has_sustained_high_intent(
        state: AgentState,
) -> bool:

    history = state.get("intent_history", [])

    if len(history) < REQUIRED_CONSECUTIVE_TURNS:
        return False

    recent = history[-REQUIRED_CONSECUTIVE_TURNS:]

    return all(
        snapshot["purchase_probability"]
        >= HIGH_INTENT_THRESHOLD
        and snapshot["interest_score"]
        >= HIGH_INTEREST_THRESHOLD
        and snapshot["confidence"]
        >= MIN_INTENT_CONFIDENCE
        for snapshot in recent
    )


def should_send_whatsapp_now(
        state: AgentState,
) -> bool:

    if state.get("live_action_triggered", False):
        return False

    if not state.get(
            "explicit_positive_signal",
            False,
    ):
        return False

    return has_sustained_high_intent(state)