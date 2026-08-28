import httpx

from app.core.config import get_settings
from app.voice.llm import LLMProvider


class SarvamLLM(LLMProvider):

    def __init__(self) -> None:
        settings = get_settings()

        self.api_key = settings.sarvam_api_key
        self.model = "sarvam-105b-conversations"

async def generate_stream(
            self,
            messages: list[dict[str, str]],
    ):
    headers = {
            "api-subscription-key": self.api_key,
            "Content-Type": "application/json",
        }

    payload = {
        "model": self.model,
        "messages": messages,
        "stream": True,
        "temperature": 0.2,
        "max_tokens": 120,
        "reasoning_effort": None,
    }

    async with httpx.AsyncClient() as client:
         async with client.stream(
            "POST",
            "https://api.sarvam.ai/v1/chat/completions",
            headers=headers,
             json=payload,
            ) as response:
              response.raise_for_status()

              async for line in response.aiter_lines():
                     if not line or line == "data: [DONE]":
                         continue

                     if line.startswith("data: "):
                        yield line[6:]