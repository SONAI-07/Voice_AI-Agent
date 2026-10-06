from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CallResponse(BaseModel):
    id: int
    customer_id: int
    agent_id: int | None
    campaign_id: int | None
    twilio_call_sid: str | None
    status: str
    started_at: datetime | None
    ended_at: datetime | None

    model_config = ConfigDict(from_attributes=True)



class OutboundCallRequest(BaseModel):
    customer_id: int
    agent_id: int
    campaign_id: int | None = None


class OutboundCallResponse(BaseModel):
    id: int
    customer_id: int
    agent_id: int | None
    campaign_id: int | None
    twilio_call_sid: str | None
    status: str

    model_config = ConfigDict(from_attributes=True)