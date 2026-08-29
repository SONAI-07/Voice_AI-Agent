from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.call import Call
from app.models.customer import Customer


class CallRepository:

    async def get_by_twilio_sid(
            self,
            session: AsyncSession,
            twilio_call_sid: str,
    ) -> Call | None:

        result = await session.execute(
            select(Call).where(
                Call.twilio_call_sid == twilio_call_sid
            )
        )

        return result.scalar_one_or_none()

    async def get_customer(
            self,
            session: AsyncSession,
            call: Call,
    ) -> Customer | None:

        result = await session.execute(
            select(Customer).where(
                Customer.id == call.customer_id
            )
        )

        return result.scalar_one_or_none()