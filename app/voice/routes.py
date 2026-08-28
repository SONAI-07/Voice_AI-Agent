from fastapi import APIRouter
from fastapi.responses import Response
from twilio.twiml.voice_response import VoiceResponse

from app.core.config import get_settings

router = APIRouter(prefix="/voice", tags=["voice"])

settings = get_settings()


@router.post("/twiml")
async def twiml() -> Response:
    response = VoiceResponse()

    connect = response.connect()
    connect.stream(
        url=f"{settings.public_base_url.replace('https://', 'wss://')}/voice/media-stream"
    )

    return Response(
        content=str(response),
        media_type="application/xml",
    )