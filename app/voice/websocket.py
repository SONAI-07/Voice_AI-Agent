import asyncio
import base64
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.voice.engine import RealtimeVoiceEngine
from app.voice.murf_tts import MurfTTS
from app.voice.sarvam_llm import SarvamLLM
from app.voice.sarvam_stt import SarvamSTT

router = APIRouter()


@router.websocket("/voice/media-stream")
async def media_stream(websocket: WebSocket):
    await websocket.accept()

    engine = RealtimeVoiceEngine(
        stt=SarvamSTT(language_code="en-IN"),
        llm=SarvamLLM(),
        tts=MurfTTS(),
    )

    await engine.start()

    async def receive_twilio_audio():
        try:
            while True:
                message = await websocket.receive_json()

                event = message.get("event")

                if event == "media":
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