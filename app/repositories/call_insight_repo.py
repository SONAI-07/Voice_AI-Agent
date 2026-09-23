from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.call import Call
from app.models.call_insights import CallInsight


class CallInsightRepository:

    async def get_by_call_for_tenant(
            self,
            session: AsyncSession,
            call_id: int,
            tenant_id: int,
    ) -> CallInsight | None:

        result = await session.execute(
            select(CallInsight)
            .join(
                Call,
                Call.id == CallInsight.call_id,
                )
            .where(
                CallInsight.call_id == call_id,
                Call.tenant_id == tenant_id,
                )
        )

        return result.scalar_one_or_none()