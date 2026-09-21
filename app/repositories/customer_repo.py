from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.customer import Customer


class CustomerRepository:


    async def get_by_id_for_tenant(
            self,
            session: AsyncSession,
            customer_id: int,
            tenant_id: int,
    ) -> Customer | None:
        """
        Return a customer only if it belongs to the supplied tenant.
        """
        result = await session.execute(
            select(Customer).where(
                Customer.id == customer_id,
                Customer.tenant_id == tenant_id,
                )
        )

        return result.scalar_one_or_none()



    async def get_by_phone_for_tenant(
            self,
            session: AsyncSession,
            phone_number: str,
            tenant_id: int,
    ) -> Customer | None:
        """
        Return a customer only if the phone number belongs
        to the supplied tenant.
        """
        result = await session.execute(
            select(Customer).where(
                Customer.phone_number == phone_number,
                Customer.tenant_id == tenant_id,
                )
        )

        return result.scalar_one_or_none()



    async def list_for_tenant(
            self,
            session: AsyncSession,
            tenant_id: int,
    ) -> list[Customer]:
        """
        Return only customers owned by the supplied tenant.
        """
        result = await session.execute(
            select(Customer)
            .where(Customer.tenant_id == tenant_id)
            .order_by(Customer.id)
        )

        return list(result.scalars().all())