import json

from app.agent.signals import EmotionSignal, IntentSignal
from app.agent.state import AgentState
from app.voice.sarvam_llm import SarvamLLM


llm = SarvamLLM()


SIGNAL_ANALYSIS_PROMPT = """
You are a conversation analysis engine for a customer-care and sales agent.

Analyze the customer's conversation so far and return ONLY valid JSON.

You must independently evaluate:

1. PURCHASE INTENT
2. EMOTIONAL STATE
3. EXPLICIT BUYING SIGNAL

Determine whether the customer's latest message contains a clear,
explicit positive signal that they want to proceed, receive details,
or see the product/brochure.

Examples of explicit positive signals:
- "Yes, I'm interested."
- "Yes, send me the details."
- "Please send the brochure."
- "I'd like to see it."
- "That sounds good, send it over."
- "Yes, I want to know more."

Do NOT mark explicit_positive_signal true merely because:
- the customer sounds happy
- the customer asks a general question
- the customer says the product sounds interesting
- the customer is polite
- the customer has high purchase intent

Return:
"explicit_positive_signal": true or false

Important:
- Emotion and purchase intent are independent signals.
- A frustrated customer can still have high purchase intent.
- A positive customer can still have low purchase intent.
- Do not infer purchase intent from emotion alone.
- Use the complete conversation context.
- Do not invent facts that are not present in the conversation.

Return exactly this JSON structure:

{
  "intent": {
    "interest_score": 0.0,
    "purchase_probability": 0.0,
    "urgency": 0.0,
    "budget_alignment": 0.0,
    "product_fit": 0.0,
    "objection_level": 0.0,
    "engagement_level": 0.0,
    "confidence": 0.0
  },
  "emotion": {
    "emotion": "positive",
    "confidence": 0.0
  },
  "explicit_positive_signal": false
}

All numeric values must be between 0.0 and 1.0.

The emotion must be exactly one of:

- positive
- neutral
- hesitant
- frustrated
- negative

Do not include markdown.
Do not include ``` fences.
Do not include any text before or after the JSON.
"""


async def analyze_signals(state: AgentState) -> AgentState:
    conversation = state["conversation"]

    messages = [
        {
            "role": "system",
            "content": SIGNAL_ANALYSIS_PROMPT,
        },
        *conversation,
    ]

    response_parts: list[str] = []

    async for chunk in llm.generate_stream(messages):
        try:
            data = json.loads(chunk)
        except json.JSONDecodeError:
            continue

        choices = data.get("choices", [])

        if not choices:
            continue

        delta = choices[0].get("delta", {})
        text = delta.get("content")

        if text:
            response_parts.append(text)

    raw_response = "".join(response_parts).strip()

    try:
        signal_data = json.loads(raw_response)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Sarvam returned invalid signal JSON: {raw_response}"
        ) from exc

        intent = IntentSignal.model_validate(
            signal_data["intent"]
        )

    emotion = EmotionSignal.model_validate(
        signal_data["emotion"]
    )

    explicit_positive_signal = signal_data.get(
        "explicit_positive_signal",
        False,
    )

    if not isinstance(explicit_positive_signal, bool):
        raise ValueError(
            "explicit_positive_signal must be a boolean"
        )

    previous_history = state.get(
        "intent_history",
        [],
    )

    new_snapshot = {
        "purchase_probability": intent.purchase_probability,
        "interest_score": intent.interest_score,
        "confidence": intent.confidence,
        "explicit_positive_signal": explicit_positive_signal,
    }

    intent_history = [
        *previous_history,
        new_snapshot,
    ]

    return {
        **state,
        "intent": intent,
        "emotion": emotion,
        "intent_history": intent_history,
        "explicit_positive_signal": explicit_positive_signal,
    }