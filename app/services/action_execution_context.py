from app.core.database import AsyncSessionLocal
from app.repositories.call_repo import CallRepository
from app.models.customer import Customer


async def get_customer_for_call(
        call_sid: str,
) -> Customer:

    call_repository = CallRepository()

    async with AsyncSessionLocal() as session:

        call = await call_repository.get_by_twilio_sid(
            session,
            call_sid,
        )

        if call is None:
            raise ValueError(
                f"Call not found for call {call_sid}"
            )

        customer = await call_repository.get_customer(
            session,
            call,
        )

        if customer is None:
            raise ValueError(
                f"Customer not found for call {call_sid}"
            )

        return customer