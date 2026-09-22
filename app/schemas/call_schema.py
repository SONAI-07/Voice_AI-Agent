from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CallResponse(BaseModel):
    id: int
    customer_id: int
    twilio_call_sid: str | None
    status: str
    started_at: datetime | None
    ended_at: datetime | None

    model_config = ConfigDict(from_attributes=True)