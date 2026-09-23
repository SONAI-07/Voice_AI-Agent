from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.Auth.dependencies import get_current_tenant
from app.core.database import get_db
from app.models.tenant import Tenant
from app.repositories.call_insight_repo import CallInsightRepository
from app.schemas.call_insight_schema import CallInsightResponse


router = APIRouter(
    prefix="/calls",
    tags=["call-insights"],
)

call_insight_repository = CallInsightRepository()


@router.get(
    "/{call_id}/insight",
    response_model=CallInsightResponse,
)
async def get_call_insight(
        call_id: int,
        tenant: Tenant = Depends(get_current_tenant),
        db: AsyncSession = Depends(get_db),
):
    insight = await call_insight_repository.get_by_call_for_tenant(
        session=db,
        call_id=call_id,
        tenant_id=tenant.id,
    )

    if insight is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call insight not found",
        )

    return insight