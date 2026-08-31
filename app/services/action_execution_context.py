from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.call import Call
from app.models.customer import Customer


async def get_customer_for_call(
        call_sid: str,
) -> Customer:

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            select(Call, Customer)
            .join(
                Customer,
                Customer.id == Call.customer_id,
                )
            .where(
                Call.twilio_call_sid == call_sid
            )
        )

        row = result.first()

        if row is None:
            raise ValueError(
                f"Customer not found for call {call_sid}"
            )

        _, customer = row

        return customer