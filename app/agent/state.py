from typing import TypedDict

from app.agent.action import ActionDecision
from app.agent.classification import ClassificationResult
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
    classification: ClassificationResult | None

    action: ActionDecision | None
    action_executed: bool