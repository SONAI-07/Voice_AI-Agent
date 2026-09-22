from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.Auth.dependencies import get_current_tenant
from app.core.database import get_db
from app.models.tenant import Tenant
from app.repositories.call_repo import CallRepository
from app.schemas.call_schema import CallResponse


router = APIRouter(
    prefix="/calls",
    tags=["calls"],
)

call_repository = CallRepository()




@router.get(
    "",
    response_model=list[CallResponse],
)
async def list_calls(
        tenant: Tenant = Depends(get_current_tenant),
        db: AsyncSession = Depends(get_db),
):
    calls = await call_repository.list_for_tenant(
        session=db,
        tenant_id=tenant.id,
    )

    return calls






@router.get(
    "/{call_id}",
    response_model=CallResponse,
)
async def get_call(
        call_id: int,
        tenant: Tenant = Depends(get_current_tenant),
        db: AsyncSession = Depends(get_db),
):
    call = await call_repository.get_by_id_for_tenant(
        session=db,
        call_id=call_id,
        tenant_id=tenant.id,
    )

    if call is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found",
        )

    return call