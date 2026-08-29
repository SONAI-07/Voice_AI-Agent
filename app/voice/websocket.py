import asyncio
import base64

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.call_memory import CallMemory
from app.voice.engine import RealtimeVoiceEngine
from app.voice.murf_tts import MurfTTS
from app.voice.sarvam_llm import SarvamLLM
from app.voice.sarvam_stt import SarvamSTT
from app.services.post_call_services import PostCallService

router = APIRouter()


@router.websocket("/voice/media-stream")
async def media_stream(websocket: WebSocket):
    await websocket.accept()

    memory = CallMemory()
    post_call_service = PostCallService(memory)
    call_sid: str | None = None

    engine = RealtimeVoiceEngine(
        stt=SarvamSTT(language_code="en-IN"),
        llm=SarvamLLM(),
        tts=MurfTTS(),
        memory=memory,
    )


    await engine.start()

    async def receive_twilio_audio():
        nonlocal call_sid

        try:
            while True:
                message = await websocket.receive_json()

                event = message.get("event")

                if event == "start":
                  start_data = message.get("start", {})

                  call_sid = start_data.get("callSid")

                  if not call_sid:

                    raise ValueError("Twilio start event missing callSid")

                  engine.set_call_sid(call_sid)

                elif event == "media":
                    payload = message["media"]["payload"]

                    audio = base64.b64decode(payload)

                    await engine.stt.send_audio(audio)

                elif event == "stop":
                    break

        except WebSocketDisconnect:
            pass

    async def process_stt():
        async for event in engine.receive_stt_events():
            event_type = event.get("type")

            if event_type == "speech_start":
                await engine.interrupt()

            elif event_type == "transcript":
                transcript = event.get("data", {}).get("transcript")

                if transcript:
                    if call_sid:
                        await memory.append_message(
                            call_sid=call_sid,
                            role="user",
                            content=transcript,
                        )

                    engine.tts_task = asyncio.create_task(
                        engine.process_transcript(transcript)
                    )

    async def send_tts_audio():
        async for audio in engine.tts.receive_audio():
            await websocket.send_json(
                {
                    "event": "media",
                    "media": {
                        "payload": base64.b64encode(audio).decode("utf-8"),
                    },
                }
            )

    try:
        await asyncio.gather(
            receive_twilio_audio(),
            process_stt(),
            send_tts_audio(),
        )

    finally:
        await engine.close()

    if call_sid:
        try:
            await post_call_service.finalize_call(
                call_sid
            )
        except Exception:
            # Do not delete Redis if post-call persistence fails.
            # Redis TTL preserves the conversation for retry.
            raise