from app.services.meta_whatsapp import MetaWhatsAppProvider
from app.services.email_provider import EmailProvider
from app.services.follow_up_provider import FollowUpProvider


class BusinessActionService:

    def __init__(self) -> None:
        self.whatsapp = MetaWhatsAppProvider()
        self.email = EmailProvider()
        self.follow_up = FollowUpProvider()

    async def send_whatsapp_brochure(
            self,
            customer_phone: str,
            idempotency_key: str,
    ) -> str:
        return await self.whatsapp.send_brochure(
            customer_phone=customer_phone,
            idempotency_key=idempotency_key,
        )

    async def send_email_brochure(
            self,
            customer_email: str,
            idempotency_key: str,
    ) -> str:
        return await self.email.send_brochure(
            customer_email=customer_email,
            idempotency_key=idempotency_key,
        )

    async def schedule_follow_up(
            self,
            customer_id: int,
            call_id: int,
            idempotency_key: str,
    ) -> str:
        return await self.follow_up.schedule(
            customer_id=customer_id,
            call_id=call_id,
            idempotency_key=idempotency_key,
        )