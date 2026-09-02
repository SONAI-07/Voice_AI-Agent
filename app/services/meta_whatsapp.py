import asyncio

import httpx

from app.core.config import get_settings
from app.observability.metrics import (
    PROVIDER_ERRORS_TOTAL,
    PROVIDER_LATENCY_SECONDS,
    PROVIDER_REQUESTS_TOTAL,
    RETRIES_TOTAL,
    TIMEOUTS_TOTAL,
)
from app.services.whatsapp import WhatsAppProvider


class MetaWhatsAppProvider(WhatsAppProvider):

    def __init__(self) -> None:
        settings = get_settings()

        if not settings.whatsapp_access_token:
            raise ValueError(
                "WhatsApp access token is not configured"
            )

        if not settings.whatsapp_phone_number_id:
            raise ValueError(
                "WhatsApp phone number ID is not configured"
            )

        self.access_token = settings.whatsapp_access_token
        self.phone_number_id = settings.whatsapp_phone_number_id
        self.api_version = settings.whatsapp_api_version

        self.template_name = (
            settings.whatsapp_brochure_template_name
        )

        self.template_language = (
            settings.whatsapp_brochure_template_language
        )

        self.url = (
            f"https://graph.facebook.com/"
            f"{self.api_version}/"
            f"{self.phone_number_id}/messages"
        )

        self.timeout = httpx.Timeout(
            timeout=15.0,
            connect=5.0,
        )

        self.max_retries = 2

    async def send_brochure(
            self,
            customer_phone: str,
            idempotency_key: str,
    ) -> str:

        if not customer_phone:
            raise ValueError(
                "customer_phone is required"
            )

        if not idempotency_key:
            raise ValueError(
                "idempotency_key is required"
            )

        payload = {
            "messaging_product": "whatsapp",
            "to": customer_phone,
            "type": "template",
            "template": {
                "name": self.template_name,
                "language": {
                    "code": self.template_language,
                },
            },
        }

        headers = {
            "Authorization": (
                f"Bearer {self.access_token}"
            ),
            "Content-Type": "application/json",
            "X-Idempotency-Key": idempotency_key,
        }

        provider = "meta_whatsapp"

        for attempt in range(self.max_retries + 1):

            started_at = asyncio.get_running_loop().time()

            PROVIDER_REQUESTS_TOTAL.labels(
                provider=provider,
                operation="send_brochure",
            ).inc()

            try:
                async with httpx.AsyncClient(
                        timeout=self.timeout,
                ) as client:

                    response = await client.post(
                        self.url,
                        json=payload,
                        headers=headers,
                    )

                latency = (
                        asyncio.get_running_loop().time()
                        - started_at
                )

                PROVIDER_LATENCY_SECONDS.labels(
                    provider=provider,
                    operation="send_brochure",
                ).observe(latency)

                # Retry only transient server-side failures.
                if response.status_code >= 500:

                    if attempt < self.max_retries:
                        RETRIES_TOTAL.labels(
                            provider=provider,
                            operation="send_brochure",
                        ).inc()

                        await asyncio.sleep(
                            0.5 * (2 ** attempt)
                        )

                        continue

                    response.raise_for_status()

                response.raise_for_status()

                data = response.json()

                messages = data.get("messages", [])

                if not messages:
                    raise ValueError(
                        "WhatsApp API returned no message ID"
                    )

                message_id = messages[0].get("id")

                if not message_id:
                    raise ValueError(
                        "WhatsApp API returned an invalid message ID"
                    )

                return message_id

            except (
                    httpx.ConnectTimeout,
                    httpx.ReadTimeout,
                    httpx.WriteTimeout,
                    httpx.PoolTimeout,
            ) as exc:

                TIMEOUTS_TOTAL.labels(
                    provider=provider,
                    operation="send_brochure",
                ).inc()

                if attempt < self.max_retries:
                    RETRIES_TOTAL.labels(
                        provider=provider,
                        operation="send_brochure",
                    ).inc()

                    await asyncio.sleep(
                        0.5 * (2 ** attempt)
                    )

                    continue

                PROVIDER_ERRORS_TOTAL.labels(
                    provider=provider,
                    operation="send_brochure",
                    error_type=type(exc).__name__,
                ).inc()

                raise

            except httpx.HTTPStatusError as exc:

                PROVIDER_ERRORS_TOTAL.labels(
                    provider=provider,
                    operation="send_brochure",
                    error_type="http_status_error",
                ).inc()

                raise

            except Exception as exc:

                PROVIDER_ERRORS_TOTAL.labels(
                    provider=provider,
                    operation="send_brochure",
                    error_type=type(exc).__name__,
                ).inc()

                raise