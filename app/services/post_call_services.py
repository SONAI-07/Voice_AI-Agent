from datetime import datetime, timezone

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.call_insights import CallInsight
from app.services.call_insight_extractor import CallInsightExtractor
from app.services.call_memory import CallMemory
from app.repositories.call_repo import CallRepository


class PostCallService:

    def __init__(
            self,
            memory: CallMemory,
    ) -> None:
        self.memory = memory
        self.extractor = CallInsightExtractor()
        self.call_repository = CallRepository()

    async def finalize_call(
            self,
            call_sid: str,
    ) -> None:

        if not call_sid:
            raise ValueError("call_sid is required")

        conversation = await self.memory.get_messages(call_sid)

        async with AsyncSessionLocal() as session:

            async with session.begin():

                call = await self.call_repository.get_by_twilio_sid(
                    session,
                    call_sid,
                )

                if call is None:
                    raise ValueError(
                        f"Call not found for Twilio SID: {call_sid}"
                    )

                customer = await self.call_repository.get_customer(
                    session,
                    call,
                )

                if customer is None:
                    raise ValueError(
                        f"Customer not found for call: {call.id}"
                    )

                # Finalize the Call record regardless of whether
                # there is enough conversation for insight extraction.
                call.status = "completed"
                call.ended_at = datetime.now(timezone.utc)

                if conversation:
                    insight = await self.extractor.extract(
                        conversation
                    )

                    existing_result = await session.execute(
                        select(CallInsight).where(
                            CallInsight.call_id == call.id
                        )
                    )

                    existing_insight = (
                        existing_result.scalar_one_or_none()
                    )

                    if existing_insight is None:
                        durable_insight = CallInsight(
                            call_id=call.id,
                            customer_id=customer.id,
                            classification=insight.classification.value,
                            purchase_probability=(
                                insight.purchase_probability
                            ),
                            interest_score=insight.interest_score,
                            summary=insight.summary,
                            important_details=(
                                insight.important_details
                            ),
                        )

                        session.add(durable_insight)

        # This happens only after the transaction above commits.
        await self.memory.delete(call_sid)