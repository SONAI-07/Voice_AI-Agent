from typing import TypedDict

from app.agent.decision import AgentDecision
from app.agent.signals import EmotionSignal, IntentSignal



class AgentState(TypedDict):
    call_sid: str
    conversation: list[dict[str, str]]
    current_transcript: str
    agent_response: str
    decision: AgentDecision | None
    next_node: str | None
    intent: IntentSignal | None
    emotion: EmotionSignal | None