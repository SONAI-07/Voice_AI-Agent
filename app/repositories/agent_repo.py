from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent


class AgentRepository:

    async def get_by_id_for_tenant(
            self,
            session: AsyncSession,
            agent_id: int,
            tenant_id: int,
    ) -> Agent | None:
        result = await session.execute(
            select(Agent).where(
                Agent.id == agent_id,
                Agent.tenant_id == tenant_id,
                Agent.is_active.is_(True),
                )
        )
        return result.scalar_one_or_none()

    async def list_for_tenant(
            self,
            session: AsyncSession,
            tenant_id: int,
    ) -> list[Agent]:
        result = await session.execute(
            select(Agent)
            .where(
                Agent.tenant_id == tenant_id,
                Agent.is_active.is_(True),
                )
            .order_by(Agent.id)
        )
        return list(result.scalars().all())