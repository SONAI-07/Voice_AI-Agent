from pydantic import BaseModel


class DashboardSummaryResponse(BaseModel):
    total_calls: int
    completed_calls: int
    failed_calls: int
    total_call_duration_seconds: float
    total_customers: int

    strong_interest_calls: int
    neutral_calls: int
    not_interested_calls: int

    whatsapp_actions_executed: int
    email_actions_executed: int
    follow_up_actions_executed: int