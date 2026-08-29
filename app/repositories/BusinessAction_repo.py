from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.business_action import BusinessActionExecution


class BusinessActionRepository:

    async def get(
            self,
            session: AsyncSession,
            call_id: int,
            action: str,
    ) -> BusinessActionExecution | None:

        result = await session.execute(
            select(BusinessActionExecution).where(
                BusinessActionExecution.call_id == call_id,
                BusinessActionExecution.action == action,
                )
        )

        return result.scalar_one_or_none()

    async def create(
            self,
            session: AsyncSession,
            call_id: int,
            action: str,
    ) -> BusinessActionExecution:

        execution = BusinessActionExecution(
            call_id=call_id,
            action=action,
            status="pending",
        )

        session.add(execution)

        await session.flush()

        return execution

    async def mark_executed(
            self,
            session: AsyncSession,
            execution: BusinessActionExecution,
    ) -> None:

        execution.status = "executed"
        execution.executed_at = datetime.now(timezone.utc)

        await session.flush()