from app.agent.classification import classify_customer
from app.agent.state import AgentState


async def classify_customer_node(state: AgentState) -> AgentState:
    intent = state["intent"]
    emotion = state["emotion"]

    if intent is None:
        raise ValueError("Intent signal is missing from state")

    if emotion is None:
        raise ValueError("Emotion signal is missing from state")

    classification = classify_customer(
        intent=intent,
        emotion=emotion,
    )

    return {
        **state,
        "classification": classification,
    }