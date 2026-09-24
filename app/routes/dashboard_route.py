from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.Auth.dependencies import get_current_tenant
from app.core.database import get_db
from app.models.business_action import BusinessActionExecution
from app.models.call import Call
from app.models.call_insights import CallInsight
from app.models.customer import Customer
from app.schemas.dashboard_schema import DashboardSummaryResponse
from app.agent.action import BusinessAction


router = APIRouter(
    prefix="/dashboard",
    tags=["dashboard"],
)


@router.get(
    "/summary",
    response_model=DashboardSummaryResponse,
)
async def get_dashboard_summary(
        tenant=Depends(get_current_tenant),
        session: AsyncSession = Depends(get_db),
) -> DashboardSummaryResponse:

    tenant_id = tenant.id

    total_calls = await session.scalar(
        select(func.count(Call.id)).where(
            Call.tenant_id == tenant_id
        )
    )

    completed_calls = await session.scalar(
        select(func.count(Call.id)).where(
            Call.tenant_id == tenant_id,
            Call.status == "completed",
            )
    )

    failed_calls = await session.scalar(
        select(func.count(Call.id)).where(
            Call.tenant_id == tenant_id,
            Call.status == "failed",
            )
    )

    total_duration = await session.scalar(
        select(
            func.coalesce(
                func.sum(
                    func.extract(
                        "epoch",
                        Call.ended_at - Call.started_at,
                        )
                ),
                0,
            )
        ).where(
            Call.tenant_id == tenant_id,
            Call.started_at.is_not(None),
            Call.ended_at.is_not(None),
            )
    )

    total_customers = await session.scalar(
        select(func.count(Customer.id)).where(
            Customer.tenant_id == tenant_id
        )
    )

    strong_interest_calls = await _count_classification(
        session,
        tenant_id,
        "STRONG",
    )

    neutral_calls = await _count_classification(
        session,
        tenant_id,
        "NEUTRAL",
    )

    not_interested_calls = await _count_classification(
        session,
        tenant_id,
        "NOT_INTERESTED",
    )

    whatsapp_actions_executed = await _count_action(
        session,
        tenant_id,
        BusinessAction.SEND_WHATSAPP_BROCHURE.value,
    )

    email_actions_executed = await _count_action(
        session,
        tenant_id,
        BusinessAction.SEND_EMAIL_BROCHURE.value,
    )

    follow_up_actions_executed = await _count_action(
        session,
        tenant_id,
        BusinessAction.SCHEDULE_FOLLOW_UP.value,
    )

    return DashboardSummaryResponse(
        total_calls=total_calls or 0,
        completed_calls=completed_calls or 0,
        failed_calls=failed_calls or 0,
        total_call_duration_seconds=float(
            total_duration or 0
        ),
        total_customers=total_customers or 0,
        strong_interest_calls=strong_interest_calls or 0,
        neutral_calls=neutral_calls or 0,
        not_interested_calls=not_interested_calls or 0,
        whatsapp_actions_executed=(
                whatsapp_actions_executed or 0
        ),
        email_actions_executed=(
                email_actions_executed or 0
        ),
        follow_up_actions_executed=(
                follow_up_actions_executed or 0
        ),
    )


async def _count_classification(
        session: AsyncSession,
        tenant_id: int,
        classification: str,
) -> int:

    result = await session.scalar(
        select(func.count(CallInsight.id))
        .join(
            Call,
            Call.id == CallInsight.call_id,
            )
        .where(
            Call.tenant_id == tenant_id,
            CallInsight.classification == classification,
            )
    )

    return result or 0


async def _count_action(
        session: AsyncSession,
        tenant_id: int,
        action: str,
) -> int:

    result = await session.scalar(
        select(func.count(BusinessActionExecution.id))
        .join(
            Call,
            Call.id == BusinessActionExecution.call_id,
            )
        .where(
            Call.tenant_id == tenant_id,
            BusinessActionExecution.action == action,
            BusinessActionExecution.status == "executed",
            )
    )

    return result or 0