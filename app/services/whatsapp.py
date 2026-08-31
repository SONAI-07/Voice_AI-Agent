from abc import ABC, abstractmethod


class WhatsAppProvider(ABC):

    @abstractmethod
    async def send_brochure(
            self,
            customer_phone: str,
            idempotency_key: str,
    ) -> str:
        """
        Send the product brochure.

        Returns:
            Provider message ID.
        """
        raise NotImplementedError