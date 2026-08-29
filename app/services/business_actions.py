from abc import ABC, abstractmethod


class BusinessActionService(ABC):

    @abstractmethod
    async def send_whatsapp_brochure(
            self,
            customer_phone: str,
    ) -> None:
        pass

    @abstractmethod
    async def send_email_brochure(
            self,
            customer_email: str,
    ) -> None:
        pass

    @abstractmethod
    async def schedule_follow_up(
            self,
            customer_id: str,
    ) -> None:
        pass