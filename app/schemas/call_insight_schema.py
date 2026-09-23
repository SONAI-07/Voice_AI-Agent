from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CallInsightResponse(BaseModel):
    id: int
    call_id: int
    customer_id: int
    classification: str
    purchase_probability: float
    interest_score: float
    summary: str
    important_details: dict
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )