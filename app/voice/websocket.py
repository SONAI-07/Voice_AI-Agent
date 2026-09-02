import asyncio
import base64
import time

from fastapi import (
    APIRouter,
    WebSocket,
    WebSocketDisconnect,
)

from app.observability.metrics import (
    CALL_DURATION_SECONDS,
    CALLS_ACTIVE,
    CALLS_TOTAL,
    POST_CALL_ERRORS_TOTAL,
    POST_CALL_LATENCY_SECONDS,
    POST_CALL_TOTAL,
    STT_EVENTS_TOTAL,
    STT_ERRORS_TOTAL,
)
from app.services.call_memory import CallMemory
from app.services.post_call_services import PostCallService
from app.voice.engine import RealtimeVoiceEngine
from app.voice.murf_tts import MurfTTS
from app.voice.sarvam_llm import SarvamLLM
from app.voice.sarvam_stt import SarvamSTT


router = APIRouter()


@router.websocket("/voice/media-stream")
async def media_stream(
        websocket: WebSocket,
):

    await websocket.accept()

    call_started_at = time.perf_counter()

    CALLS_TOTAL.labels(
        environment="production"
    ).inc()

    CALLS_ACTIVE.inc()

    memory = CallMemory()

    post_call_service = PostCallService(
        memory=memory
    )

    call_sid: str | None = None

    engine = RealtimeVoiceEngine(
        stt=SarvamSTT(
            language_code="en-IN"
        ),
        llm=SarvamLLM(),
        tts=MurfTTS(),
        memory=memory,
    )

    await engine.start()

    async def receive_twilio_audio():

        nonlocal call_sid

        try:

            while True:

                message = (
                    await websocket.receive_json()
                )

                event = message.get(
                    "event"
                )

                STT_EVENTS_TOTAL.labels(
                    event_type=event or "unknown"
                ).inc()

                if event == "start":

                    start_data = message.get(
                        "start",
                        {},
                    )

                    call_sid = start_data.get(
                        "callSid"
                    )

                    if not call_sid:

                        raise ValueError(
                            "Twilio start event "
                            "missing callSid"
                        )

                    engine.set_call_sid(
                        call_sid
                    )

                elif event == "media":

                    payload = (
                        message["media"]["payload"]
                    )

                    audio = base64.b64decode(
                        payload
                    )

                    await engine.stt.send_audio(
                        audio
                    )

                elif event == "stop":

                    break

        except WebSocketDisconnect:

            pass

        except Exception as exc:

            STT_ERRORS_TOTAL.labels(
                error_type=type(exc).__name__
            ).inc()

            raise

    async def process_stt():

        async for event in (engine.receive_stt_events()):

            event_type = event.get("type", "unknown")

            STT_EVENTS_TOTAL.labels(
                event_type=event_type
            ).inc()

            if event_type == "speech_start":

                await engine.interrupt()

            elif event_type == "transcript":

                transcript = (
                    event
                    .get("data", {})
                    .get("transcript")
                )

                if not transcript:
                    continue

                if not call_sid:
                    continue

                await memory.append_message(
                    call_sid=call_sid,
                    role="user",
                    content=transcript,
                )

                await engine.submit_transcript(
                    transcript
                )

    async def send_tts_audio():

        async for audio in (
                engine.tts.receive_audio()
        ):

            await websocket.send_json(
                {
                    "event": "media",
                    "media": {
                        "payload": (
                            base64.b64encode(
                                audio
                            ).decode("utf-8")
                        ),
                    },
                }
            )

    receive_task = asyncio.create_task(
        receive_twilio_audio()
    )

    stt_task = asyncio.create_task(
        process_stt()
    )

    tts_audio_task = asyncio.create_task(
        send_tts_audio()
    )

    try:

        await receive_task

    except WebSocketDisconnect:

        pass

    finally:

        # =========================================================
        # STOP INPUT
        # =========================================================

        stt_task.cancel()

        await asyncio.gather(
            stt_task,
            return_exceptions=True,
        )

        # =========================================================
        # STOP OUTPUT
        # =========================================================

        tts_audio_task.cancel()

        await asyncio.gather(
            tts_audio_task,
            return_exceptions=True,
        )

        # =========================================================
        # WAIT FOR AGENT
        # =========================================================

        try:

            await asyncio.wait_for(
                engine.wait_for_agent_tasks(),
                timeout=15.0,
            )

        except asyncio.TimeoutError:

            await engine.cancel_agent_tasks()

        # =========================================================
        # CLOSE PROVIDERS
        # =========================================================

        await engine.close()

        # =========================================================
        # POST CALL
        # =========================================================

        if call_sid:

            POST_CALL_TOTAL.inc()

            post_call_started_at = (
                time.perf_counter()
            )

            try:

                await post_call_service.finalize_call(
                    call_sid
                )

            except Exception as exc:

                POST_CALL_ERRORS_TOTAL.labels(
                    error_type=type(exc).__name__
                ).inc()

                raise

            finally:

                POST_CALL_LATENCY_SECONDS.observe(
                    time.perf_counter()
                    - post_call_started_at
                )

        # =========================================================
        # CALL METRICS
        # =========================================================

        CALL_DURATION_SECONDS.observe(
            time.perf_counter()
            - call_started_at
        )

        CALLS_ACTIVE.dec()