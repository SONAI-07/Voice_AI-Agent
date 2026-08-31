from typing import TypedDict

from app.agent.action import ActionDecision
from app.agent.classification import ClassificationResult
from app.agent.decision import AgentDecision
from app.agent.signals import EmotionSignal, IntentSignal


class IntentSnapshot(TypedDict):
    purchase_probability: float
    interest_score: float
    confidence: float
    explicit_positive_signal: bool


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

    intent_history: list[IntentSnapshot]

    explicit_positive_signal: bool
    sustained_high_intent: bool
    live_action_triggered: bool

    action: ActionDecision | None
    action_executed: bool