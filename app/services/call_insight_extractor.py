import json

from app.services.insight_classification import CallInsightData
from app.voice.sarvam_llm import SarvamLLM


POST_CALL_SYSTEM_PROMPT = """
You are a post-call analysis system for a customer-care and sales agent.

Analyze the complete conversation and extract only durable,
business-relevant customer information.

Determine:
- classification
- purchase_probability
- interest_score
- summary
- important_details

Classification rules:
- strong: clear buying intent and meaningful product interest
- not_interested: clear rejection or lack of interest
- neutral: uncertain, exploratory, or insufficient buying intent

Emotion must NOT be used as a substitute for purchase intent.
A frustrated customer can still have high purchase intent.

Do not invent information.
Only include important_details explicitly supported by the conversation.

Return ONLY valid JSON matching this structure:

{
  "classification": "strong | neutral | not_interested",
  "purchase_probability": 0.0,
  "interest_score": 0.0,
  "summary": "...",
  "important_details": {}
}
"""


class CallInsightExtractor:

    def __init__(self) -> None:
        self.llm = SarvamLLM()

    async def extract(
            self,
            conversation: list[dict[str, str]],
    ) -> CallInsightData:

        if not conversation:
            raise ValueError(
                "Cannot extract call insight from empty conversation"
            )

        messages = [
            {
                "role": "system",
                "content": POST_CALL_SYSTEM_PROMPT,
            },
            *conversation,
        ]

        response_parts: list[str] = []

        async for chunk in self.llm.generate_stream(messages):
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

        if not raw_response:
            raise ValueError(
                "Sarvam returned an empty post-call insight"
            )

        try:
            insight_data = json.loads(raw_response)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Sarvam returned invalid insight JSON: {raw_response}"
            ) from exc

        return CallInsightData.model_validate(insight_data)