from app.agent.action import determine_business_action
from app.agent.state import AgentState


async def determine_action_node(state: AgentState) -> AgentState:
    classification = state["classification"]

    if classification is None:
        raise ValueError("Classification is missing from state")

    action = determine_business_action(classification)

    return {
        **state,
        "action": action,
    }