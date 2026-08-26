from fastapi import APIRouter
from fastapi.responses import Response
from twilio.twiml.voice_response import VoiceResponse

router = APIRouter(prefix="/voice", tags=["voice"])


@router.post("/twiml")
async def twiml() -> Response:
    response = VoiceResponse()
    response.say("Hello. This is a test call from CustomerCare Agent.")

    return Response(
        content=str(response),
        media_type="application/xml",
    )
