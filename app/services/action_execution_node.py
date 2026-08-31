from app.agent.action import BusinessAction
from app.agent.state import AgentState
from app.services.business_action_executor import BusinessActionExecutor
from app.services.business_actions import BusinessActionService
from app.services.action_execution_context import (
    get_customer_for_call,
)


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
        raise ValueError(
            "Business action is missing from state"
        )

    if action.action != BusinessAction.SEND_WHATSAPP_BROCHURE:
        return {
            **state,
            "action_executed": False,
        }

    customer = await get_customer_for_call(
        state["call_sid"]
    )

    if not customer.phone_number:
        raise ValueError(
            "Customer has no phone number"
        )

    executor = BusinessActionExecutor(
        service=BusinessActionService()
    )

    await executor.execute(
        action,
        call_sid=state["call_sid"],
        customer_phone=customer.phone_number,
    )

    return {
        **state,
        "action_executed": True,
        "live_action_triggered": True,
    }