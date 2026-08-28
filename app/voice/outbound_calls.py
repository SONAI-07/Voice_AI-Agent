from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import get_settings
from app.voice.twillio import twilio_client
from main import app
from app.voice.outbound_calls import router as calls_router

app.include_router(calls_router)

router = APIRouter(prefix="/calls", tags=["calls"])


settings = get_settings()


class OutboundCallRequest(BaseModel):
    phone_number: str


@router.post("/outbound")
async def outbound_call(request: OutboundCallRequest):
    call = twilio_client.calls.create(
        to=request.phone_number,
        from_=settings.twilio_phone_number,
        url=f"{settings.public_base_url}/voice/twiml",
    )

    return {
        "call_sid": call.sid,
        "status": call.status,
    }