from app.agent.action import BusinessAction
from app.agent.state import AgentState
from app.services.action_executor import BusinessActionExecutor
from app.services.business_actions import BusinessActionService


class MockBusinessActionService(BusinessActionService):

    async def send_whatsapp_brochure(
            self,
            customer_phone: str,
    ) -> None:
        print(
            f"[MOCK] Sending WhatsApp brochure to {customer_phone}"
        )

    async def send_email_brochure(
            self,
            customer_email: str,
    ) -> None:
        print(
            f"[MOCK] Sending email brochure to {customer_email}"
        )

    async def schedule_follow_up(
            self,
            customer_id: str,
    ) -> None:
        print(
            f"[MOCK] Scheduling follow-up for {customer_id}"
        )


async def execute_business_action(
        state: AgentState,
) -> AgentState:

    action = state["action"]

    if action is None:
        raise ValueError("Business action is missing from state")

    executor = BusinessActionExecutor(
        service=MockBusinessActionService()
    )

    await executor.execute(
        action,
        customer_phone=None,
        customer_email=None,
        customer_id=state["call_sid"],
    )

    return {
        **state,
        "action_executed": True,
    }