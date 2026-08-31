from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.follow_up import FollowUp


class FollowUpProvider:

    async def schedule(
            self,
            customer_id: int,
            call_id: int,
            idempotency_key: str,
    ) -> str:

        scheduled_at = (
                datetime.now(timezone.utc)
                + timedelta(hours=24)
        )

        async with AsyncSessionLocal() as session:

            existing = await session.execute(
                select(FollowUp).where(
                    FollowUp.call_id == call_id
                )
            )

            follow_up = existing.scalar_one_or_none()

            if follow_up is not None:
                return str(follow_up.id)

            follow_up = FollowUp(
                customer_id=customer_id,
                call_id=call_id,
                scheduled_at=scheduled_at,
                status="scheduled",
            )

            session.add(follow_up)

            await session.commit()
            await session.refresh(follow_up)

            return str(follow_up.id)