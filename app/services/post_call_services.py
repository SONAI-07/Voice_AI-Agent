from datetime import datetime, timezone

from sqlalchemy import select

from app.agent.action import (
    ActionDecision,
    BusinessAction,
)
from app.agent.classification import CustomerClassification
from app.core.database import AsyncSessionLocal
from app.models.call_insights import CallInsight
from app.services.business_action_executor import BusinessActionExecutor
from app.services.business_actions import BusinessActionService
from app.services.call_insight_extractor import CallInsightExtractor
from app.services.call_memory import CallMemory
from app.services.deferred_action_policy import (
    determine_post_call_action,
)
from app.repositories.call_repo import CallRepository
from app.models.business_action import BusinessActionExecution


class PostCallService:

    def __init__(
            self,
            memory: CallMemory,
    ) -> None:

        self.memory = memory
        self.extractor = CallInsightExtractor()
        self.call_repository = CallRepository()

        self.action_executor = BusinessActionExecutor(
            service=BusinessActionService()
        )

    async def finalize_call(
            self,
            call_sid: str,
    ) -> None:

        if not call_sid:
            raise ValueError("call_sid is required")

        conversation = await self.memory.get_messages(
            call_sid
        )

        async with AsyncSessionLocal() as session:

            call = await self.call_repository.get_by_twilio_sid(
                session,
                call_sid,
            )

            if call is None:
                raise ValueError(
                    f"Call not found: {call_sid}"
                )

            customer = await self.call_repository.get_customer(
                session,
                call,
            )

            if customer is None:
                raise ValueError(
                    f"Customer not found: {call.id}"
                )

        # LLM work happens OUTSIDE the DB transaction.
        insight = None

        if conversation:
            insight = await self.extractor.extract(
                conversation
            )

        async with AsyncSessionLocal() as session:

            async with session.begin():

                call = await self.call_repository.get_by_twilio_sid(
                    session,
                    call_sid,
                )

                if call is None:
                    raise ValueError(
                        f"Call not found: {call_sid}"
                    )

                customer = await self.call_repository.get_customer(
                    session,
                    call,
                )

                if customer is None:
                    raise ValueError(
                        f"Customer not found: {call.id}"
                    )

                call.status = "completed"
                call.ended_at = datetime.now(timezone.utc)

                if insight is not None:

                    existing = await session.execute(
                        select(CallInsight).where(
                            CallInsight.call_id == call.id
                        )
                    )

                    existing_insight = (
                        existing.scalar_one_or_none()
                    )

                    if existing_insight is None:

                        session.add(
                            CallInsight(
                                call_id=call.id,
                                customer_id=customer.id,
                                classification=(
                                    insight.classification.value
                                ),
                                purchase_probability=(
                                    insight.purchase_probability
                                ),
                                interest_score=(
                                    insight.interest_score
                                ),
                                summary=insight.summary,
                                important_details=(
                                    insight.important_details
                                ),
                            )
                        )

        if insight is None:
            await self.memory.delete(call_sid)
            return

        # Never repeat a live WhatsApp action after it already succeeded.
        async with AsyncSessionLocal() as session:

            result = await session.execute(
                select(
                    CallInsight,
                )
                .where(
                    CallInsight.call_id == call.id
                )
            )

        whatsapp_already_sent = (
            await self._whatsapp_was_sent(call.id)
        )

        deferred_action = determine_post_call_action(
            classification=(
                insight.classification
            ),
            whatsapp_already_sent=whatsapp_already_sent,
        )

        if deferred_action is not None:

            action = ActionDecision(
                action=deferred_action,
                classification=(
                    insight.classification
                ),
            )

            await self.action_executor.execute(
                action,
                call_sid=call_sid,
                customer_phone=customer.phone_number,
                customer_email=customer.email,
                customer_id=customer.id,
            )

        # IMPORTANT:
        # Only successful durable processing reaches this point.
        await self.memory.delete(call_sid)

    async def _whatsapp_was_sent(
            self,
            call_id: int,
    ) -> bool:

     async with AsyncSessionLocal() as session:

        result = await session.execute(
            select(BusinessActionExecution).where(
                BusinessActionExecution.call_id == call_id,
                BusinessActionExecution.action
                == BusinessAction.SEND_WHATSAPP_BROCHURE.value,
                BusinessActionExecution.status
                == "executed",
                )
        )

        return result.scalar_one_or_none() is not None