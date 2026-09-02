import asyncio
import json
import time
from collections.abc import AsyncIterator

import httpx

from app.core.config import get_settings
from app.observability.metrics import (
    PROVIDER_ERRORS_TOTAL,
    PROVIDER_LATENCY_SECONDS,
    PROVIDER_REQUESTS_TOTAL,
    RETRIES_TOTAL,
    TIMEOUTS_TOTAL,
)
from app.voice.llm import LLMProvider


SARVAM_LLM_URL = (
    "https://api.sarvam.ai/v1/chat/completions"
)

SARVAM_LLM_TIMEOUT_SECONDS = 30.0
SARVAM_LLM_CONNECT_TIMEOUT_SECONDS = 10.0

SARVAM_LLM_MAX_RETRIES = 2


class SarvamLLM(LLMProvider):

    def __init__(self) -> None:

        settings = get_settings()

        if not settings.sarvam_api_key:
            raise ValueError(
                "SARVAM_API_KEY is not configured"
            )

        self.api_key = settings.sarvam_api_key

        self.model = (
            "sarvam-105b-conversations"
        )

        self.timeout = httpx.Timeout(
            timeout=SARVAM_LLM_TIMEOUT_SECONDS,
            connect=SARVAM_LLM_CONNECT_TIMEOUT_SECONDS,
        )

    async def generate_stream(
            self,
            messages: list[dict[str, str]],
    ) -> AsyncIterator[str]:
        """
        Generate a streaming Sarvam response.

        Retry policy:
        - Retry connection/request establishment.
        - Do not retry after the streaming response
          has successfully started.
        """

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

        for attempt in range(
                SARVAM_LLM_MAX_RETRIES + 1
        ):

            PROVIDER_REQUESTS_TOTAL.labels(
                provider="sarvam_llm",
                operation="generate_stream",
            ).inc()

            started_at = time.perf_counter()

            try:

                async with httpx.AsyncClient(
                        timeout=self.timeout,
                ) as client:

                    async with client.stream(
                            "POST",
                            SARVAM_LLM_URL,
                            headers=headers,
                            json=payload,
                    ) as response:

                        response.raise_for_status()

                        PROVIDER_LATENCY_SECONDS.labels(
                            provider="sarvam_llm",
                            operation="stream_start",
                        ).observe(
                            time.perf_counter()
                            - started_at
                        )

                        # ------------------------------------------------
                        # IMPORTANT:
                        #
                        # Once we successfully enter the streaming
                        # response, retrying is unsafe because the
                        # consumer may already have received tokens.
                        # ------------------------------------------------

                        async for line in response.aiter_lines():

                            if not line:
                                continue

                            if line == "data: [DONE]":
                                break

                            if line.startswith("data: "):

                                yield line[6:]

                        return

            except asyncio.CancelledError:
                raise

            except (
                    httpx.ConnectTimeout,
                    httpx.ReadTimeout,
                    httpx.WriteTimeout,
                    httpx.PoolTimeout,
            ) as exc:

                TIMEOUTS_TOTAL.labels(
                    provider="sarvam_llm",
                    operation="generate_stream",
                ).inc()

                PROVIDER_ERRORS_TOTAL.labels(
                    provider="sarvam_llm",
                    operation="generate_stream",
                    error_type=type(exc).__name__,
                ).inc()

                if attempt >= SARVAM_LLM_MAX_RETRIES:
                    raise

                RETRIES_TOTAL.labels(
                    provider="sarvam_llm",
                    operation="generate_stream",
                ).inc()

                await asyncio.sleep(
                    0.5 * (2 ** attempt)
                )

            except httpx.HTTPStatusError as exc:

                PROVIDER_ERRORS_TOTAL.labels(
                    provider="sarvam_llm",
                    operation="generate_stream",
                    error_type=(
                        f"http_{exc.response.status_code}"
                    ),
                ).inc()

                # Do not retry authentication or malformed
                # requests. Retry only transient server errors.
                if (
                        exc.response.status_code < 500
                        or attempt >= SARVAM_LLM_MAX_RETRIES
                ):
                    raise

                RETRIES_TOTAL.labels(
                    provider="sarvam_llm",
                    operation="generate_stream",
                ).inc()

                await asyncio.sleep(
                    0.5 * (2 ** attempt)
                )

            except httpx.HTTPError as exc:

                PROVIDER_ERRORS_TOTAL.labels(
                    provider="sarvam_llm",
                    operation="generate_stream",
                    error_type=type(exc).__name__,
                ).inc()

                if attempt >= SARVAM_LLM_MAX_RETRIES:
                    raise

                RETRIES_TOTAL.labels(
                    provider="sarvam_llm",
                    operation="generate_stream",
                ).inc()

                await asyncio.sleep(
                    0.5 * (2 ** attempt)
                )

            except Exception as exc:

                PROVIDER_ERRORS_TOTAL.labels(
                    provider="sarvam_llm",
                    operation="generate_stream",
                    error_type=type(exc).__name__,
                ).inc()

                raise