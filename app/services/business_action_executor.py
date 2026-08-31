from uuid import NAMESPACE_URL, uuid5

from app.agent.action import ActionDecision, BusinessAction
from app.core.database import AsyncSessionLocal
from app.repositories.BusinessAction_repo import (
    BusinessActionRepository,
)
from app.repositories.call_repo import CallRepository
from app.services.business_actions import BusinessActionService


class BusinessActionExecutor:

    def __init__(
            self,
            service: BusinessActionService,
    ) -> None:
        self.service = service
        self.action_repository = BusinessActionRepository()
        self.call_repository = CallRepository()

    async def execute(
            self,
            action: ActionDecision,
            *,
            call_sid: str,
            customer_phone: str | None = None,
            customer_email: str | None = None,
            customer_id: int | None = None,
    ) -> None:

        if not call_sid:
            raise ValueError("call_sid is required")

        async with AsyncSessionLocal() as session:

            call = await self.call_repository.get_by_twilio_sid(
                session,
                call_sid,
            )

            if call is None:
                raise ValueError(
                    f"Call not found: {call_sid}"
                )

            existing = await self.action_repository.get(
                session,
                call.id,
                action.action.value,
            )

            if existing is not None:

                if existing.status == "executed":
                    return

                if existing.status == "pending":
                    raise RuntimeError(
                        f"Action already pending: "
                        f"{action.action.value}"
                    )

            execution = await self.action_repository.create(
                session,
                call.id,
                action.action.value,
            )

            await session.commit()

        idempotency_key = str(
            uuid5(
                NAMESPACE_URL,
                f"customer-care:"
                f"{call.id}:"
                f"{action.action.value}",
            )
        )

        if action.action == BusinessAction.SEND_WHATSAPP_BROCHURE:

            if not customer_phone:
                raise ValueError(
                    "customer_phone is required"
                )

            await self.service.send_whatsapp_brochure(
                customer_phone=customer_phone,
                idempotency_key=idempotency_key,
            )

        elif action.action == BusinessAction.SEND_EMAIL_BROCHURE:

            if not customer_email:
                raise ValueError(
                    "customer_email is required"
                )

            await self.service.send_email_brochure(
                customer_email=customer_email,
                idempotency_key=idempotency_key,
            )

        elif action.action == BusinessAction.SCHEDULE_FOLLOW_UP:

            if customer_id is None:
                raise ValueError(
                    "customer_id is required"
                )

            await self.service.schedule_follow_up(
                customer_id=customer_id,
                call_id=call.id,
                idempotency_key=idempotency_key,
            )

        else:
            raise ValueError(
                f"Unsupported business action: "
                f"{action.action.value}"
            )

        async with AsyncSessionLocal() as session:

            result = await self.action_repository.get(
                session,
                call.id,
                action.action.value,
            )

            if result is None:
                raise RuntimeError(
                    "Business action execution disappeared"
                )

            await self.action_repository.mark_executed(
                session,
                result,
            )

            await session.commit()