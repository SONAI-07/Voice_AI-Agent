from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import get_settings
from app.voice.twillio import create_outbound_call

router = APIRouter(prefix="/calls", tags=["calls"])

settings = get_settings()


class OutboundCallRequest(BaseModel):
    phone_number: str


@router.post("/outbound")
async def outbound_call(request: OutboundCallRequest):
    twiml_url = f"{settings.public_base_url}/voice/twiml"

    call = create_outbound_call(
        to_number=request.phone_number,
        twiml_url=twiml_url,
    )

    return {
        "call_sid": call.sid,
        "status": call.status,
    }