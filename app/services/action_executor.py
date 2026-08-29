from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.action import ActionDecision, BusinessAction
from app.repositories.BusinessAction_repo import BusinessActionRepository
from app.services.business_actions import BusinessActionService


class BusinessActionExecutor:

    def __init__(
            self,
            service: BusinessActionService,
            repository: BusinessActionRepository,
    ) -> None:
        self.service = service
        self.repository = repository

    async def execute(
            self,
            session: AsyncSession,
            *,
            call_id: int,
            action: ActionDecision,
            customer_phone: str | None = None,
            customer_email: str | None = None,
            customer_id: str | None = None,
    ) -> bool:

        action_name = action.action.value

        existing = await self.repository.get(
            session,
            call_id,
            action_name,
        )

        if existing is not None:
            if existing.status == "executed":
                return False

            raise RuntimeError(
                f"Business action already exists in state: "
                f"{existing.status}"
            )

        try:
            execution = await self.repository.create(
                session,
                call_id,
                action_name,
            )

            await session.commit()

        except IntegrityError:
            await session.rollback()

            return False

        if action.action == BusinessAction.SEND_WHATSAPP_BROCHURE:
            if not customer_phone:
                raise ValueError(
                    "Customer phone is required for WhatsApp brochure"
                )

            await self.service.send_whatsapp_brochure(
                customer_phone
            )

        elif action.action == BusinessAction.SEND_EMAIL_BROCHURE:
            if not customer_email:
                raise ValueError(
                    "Customer email is required for email brochure"
                )

            await self.service.send_email_brochure(
                customer_email
            )

        elif action.action == BusinessAction.SCHEDULE_FOLLOW_UP:
            if not customer_id:
                raise ValueError(
                    "Customer ID is required for follow-up scheduling"
                )

            await self.service.schedule_follow_up(
                customer_id
            )

        elif action.action in {
            BusinessAction.CONTINUE_CONVERSATION,
            BusinessAction.END_SALES_WORKFLOW,
        }:
            await self.repository.mark_executed(
                session,
                execution,
            )
            await session.commit()

            return True

        else:
            raise ValueError(
                f"Unsupported business action: {action.action}"
            )

        await self.repository.mark_executed(
            session,
            execution,
        )

        await session.commit()

        return True