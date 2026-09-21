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
        """
        Internal/provider lookup.

        Used by the Twilio/WebSocket/PostCall lifecycle where there is
        no authenticated SaaS user or tenant context.

        Tenant ownership is recovered from the trusted Call record itself.
        """
        result = await session.execute(
            select(Call).where(
                Call.twilio_call_sid == twilio_call_sid
            )
        )
        return result.scalar_one_or_none()


    async def get_by_id_for_tenant(
            self,
            session: AsyncSession,
            call_id: int,
            tenant_id: int,
    ) -> Call | None:
        """
        Tenant-scoped lookup for authenticated SaaS operations.

        A call is accessible only when it belongs to the supplied tenant.
        """
        result = await session.execute(
            select(Call).where(
                Call.id == call_id,
                Call.tenant_id == tenant_id,
                )
        )
        return result.scalar_one_or_none()


    async def get_by_twilio_sid_for_tenant(
            self,
            session: AsyncSession,
            twilio_call_sid: str,
            tenant_id: int,
    ) -> Call | None:
        """
        Tenant-scoped Twilio SID lookup.

        Intended for authenticated application-level operations where
        both the Twilio SID and authenticated tenant are available.
        """
        result = await session.execute(
            select(Call).where(
                Call.twilio_call_sid == twilio_call_sid,
                Call.tenant_id == tenant_id,
                )
        )
        return result.scalar_one_or_none()



    async def get_customer(
            self,
            session: AsyncSession,
            call: Call,
    ) -> Customer | None:
        """
        Internal lookup through an already-resolved Call.

        The Call itself is the ownership boundary here.
        """
        result = await session.execute(
            select(Customer).where(
                Customer.id == call.customer_id,
                Customer.tenant_id == call.tenant_id,
                )
        )
        return result.scalar_one_or_none()