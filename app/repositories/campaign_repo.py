from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import Campaign


class CampaignRepository:

    async def get_by_id_for_tenant(
            self,
            session: AsyncSession,
            campaign_id: int,
            tenant_id: int,
    ) -> Campaign | None:
        result = await session.execute(
            select(Campaign).where(
                Campaign.id == campaign_id,
                Campaign.tenant_id == tenant_id,
                Campaign.is_active.is_(True),
                )
        )
        return result.scalar_one_or_none()

    async def list_for_tenant(
            self,
            session: AsyncSession,
            tenant_id: int,
    ) -> list[Campaign]:
        result = await session.execute(
            select(Campaign)
            .where(
                Campaign.tenant_id == tenant_id,
                Campaign.is_active.is_(True),
                )
            .order_by(Campaign.id)
        )
        return list(result.scalars().all())