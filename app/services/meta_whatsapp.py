import httpx

from app.core.config import get_settings
from app.services.whatsapp import WhatsAppProvider


class MetaWhatsAppProvider(WhatsAppProvider):

    def __init__(self) -> None:
        settings = get_settings()

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

    async def send_brochure(
            self,
            customer_phone: str,
            idempotency_key: str,
    ) -> str:

        if not customer_phone:
            raise ValueError(
                "customer_phone is required"
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
        }

        # The idempotency key is retained at our service boundary.
        # The provider request can be extended with provider-specific
        # idempotency support when available.
        headers["X-Idempotency-Key"] = idempotency_key

        async with httpx.AsyncClient(
                timeout=15.0,
        ) as client:

            response = await client.post(
                self.url,
                json=payload,
                headers=headers,
            )

            response.raise_for_status()

            data = response.json()

        messages = data.get("messages", [])

        if not messages:
            raise ValueError(
                f"WhatsApp API returned no message ID: {data}"
            )

        return messages[0]["id"]