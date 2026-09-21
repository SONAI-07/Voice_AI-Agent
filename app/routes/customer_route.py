from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.Auth.dependencies import get_current_tenant
from app.core.database import get_db
from app.models.tenant import Tenant
from app.repositories.customer_repo import CustomerRepository
from app.schemas.customer_schema import CustomerResponse


router = APIRouter(
    prefix="/customers",
    tags=["customers"],
)

customer_repository = CustomerRepository()


@router.get(
    "",
    response_model=list[CustomerResponse],
)
async def list_customers(
        tenant: Tenant = Depends(get_current_tenant),
        db: AsyncSession = Depends(get_db),
):
    customers = await customer_repository.list_for_tenant(
        session=db,
        tenant_id=tenant.id,
    )

    return customers