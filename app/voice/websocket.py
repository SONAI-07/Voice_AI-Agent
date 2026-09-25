import asyncio
import base64
import time

from fastapi import (
    APIRouter,
    WebSocket,
    WebSocketDisconnect,
)
from datetime import datetime, timezone
from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
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
from app.repositories.call_repo import CallRepository
from app.services.call_memory import CallMemory
from app.services.post_call_services import PostCallService
from app.voice.engine import RealtimeVoiceEngine
from app.voice.murf_tts import MurfTTS
from app.voice.sarvam_llm import SarvamLLM
from app.voice.sarvam_stt import SarvamSTT


router = APIRouter()


@router.websocket("/voice/media-stream")
async def media_stream(websocket: WebSocket):
    await websocket.accept()

    settings = get_settings()
    call_started_at = time.perf_counter()

    CALLS_TOTAL.labels(environment=settings.app_env).inc()
    CALLS_ACTIVE.inc()

    call_sid: str | None = None
    call_validated = False

    memory = CallMemory()
    post_call_service = PostCallService(memory=memory)

    engine: RealtimeVoiceEngine | None = None

    stt_task: asyncio.Task | None = None
    tts_audio_task: asyncio.Task | None = None

    try:
        # =========================================================
        # TWILIO INPUT
        # =========================================================
        async def receive_twilio_audio():
            nonlocal call_sid
            nonlocal call_validated
            nonlocal engine
            nonlocal stt_task
            nonlocal tts_audio_task

            try:
                while True:
                    message = await websocket.receive_json()
                    event = message.get("event")

                    STT_EVENTS_TOTAL.labels(
                        event_type=event or "unknown"
                    ).inc()

                    # =================================================
                    # TWILIO START
                    # =================================================
                    if event == "start":
                        start_data = message.get("start", {})
                        call_sid = start_data.get("callSid")

                        if not call_sid:
                            raise ValueError(
                                "Twilio start event missing callSid"
                            )

                        # =================================================
                        # PHASE 4.3
                        # DURABLE CALL OWNERSHIP RECOVERY
                        # =================================================
                        call_repository = CallRepository()

                        async with AsyncSessionLocal() as session:
                            call = await call_repository.get_by_twilio_sid(
                                session=session,
                                twilio_call_sid=call_sid,
                            )

                        if call is None:
                            raise ValueError(
                                "Unknown Twilio call SID"
                            )
                        call.started_at = datetime.now(timezone.utc)
                        await session.commit()

                        # The provider call SID has now been resolved
                        # to an authoritative durable Call record.
                        # The provider call SID has now been resolved
                        # to an authoritative durable Call record.
                        call_validated = True

                        # Mark the actual beginning of the voice runtime.
                        # The Call record was already created by the control plane,
                        # so this timestamp represents when the provider actually
                        # entered the voice execution lifecycle.
                        async with AsyncSessionLocal() as session:
                            async with session.begin():
                             call.started_at = datetime.now(timezone.utc)



                        # =================================================
                        # START VOICE RUNTIME ONLY AFTER CALL VALIDATION
                        # =================================================
                        engine = RealtimeVoiceEngine(
                            stt=SarvamSTT(language_code="en-IN"),
                            llm=SarvamLLM(),
                            tts=MurfTTS(),
                            memory=memory,
                        )

                        await engine.start()
                        engine.set_call_sid(call_sid)

                        # Start STT/TTS workers only after the durable
                        # Call ownership has been established.
                        stt_task = asyncio.create_task(
                            process_stt()
                        )

                        tts_audio_task = asyncio.create_task(
                            send_tts_audio()
                        )

                    # =================================================
                    # TWILIO MEDIA
                    # =================================================
                    elif event == "media":
                        # Twilio should send the start event before media.
                        # Do not process media unless the runtime has
                        # successfully started and the Call was validated.
                        if engine is None or not call_validated:
                            raise ValueError(
                                "Received media before call validation"
                            )

                        payload = message["media"]["payload"]
                        audio = base64.b64decode(payload)

                        await engine.stt.send_audio(audio)

                    # =================================================
                    # TWILIO STOP
                    # =================================================
                    elif event == "stop":
                        break

            except WebSocketDisconnect:
                pass

            except Exception as exc:
                STT_ERRORS_TOTAL.labels(
                    error_type=type(exc).__name__
                ).inc()
                raise

        # =========================================================
        # STT EVENT PROCESSING
        # =========================================================
        async def process_stt():
            if engine is None:
                return

            async for event in engine.receive_stt_events():
                event_type = event.get("type", "unknown")

                STT_EVENTS_TOTAL.labels(
                    event_type=event_type
                ).inc()

                if event_type == "speech_start":
                    await engine.interrupt()

                elif event_type == "transcript":
                    transcript = (
                        event.get("data", {})
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

        # =========================================================
        # TTS OUTPUT
        # =========================================================
        async def send_tts_audio():
            if engine is None:
                return

            async for audio in engine.tts.receive_audio():
                await websocket.send_json(
                    {
                        "event": "media",
                        "media": {
                            "payload": base64.b64encode(
                                audio
                            ).decode("utf-8"),
                        },
                    }
                )

        # =========================================================
        # RECEIVE TASK
        #
        # STT/TTS tasks are deliberately NOT started here.
        # They are started only after the Twilio start event has
        # produced a valid durable Call.
        # =========================================================
        receive_task = asyncio.create_task(
            receive_twilio_audio()
        )

        try:
            await receive_task

        except WebSocketDisconnect:
            pass

        finally:
            # =====================================================
            # STOP STT INPUT PROCESSING
            # =====================================================
            if stt_task is not None:
                stt_task.cancel()

                await asyncio.gather(
                    stt_task,
                    return_exceptions=True,
                )

            # =====================================================
            # STOP TTS OUTPUT
            # =====================================================
            if tts_audio_task is not None:
                tts_audio_task.cancel()

                await asyncio.gather(
                    tts_audio_task,
                    return_exceptions=True,
                )

            # =====================================================
            # WAIT FOR AGENT
            # =====================================================
            if engine is not None:
                try:
                    await asyncio.wait_for(
                        engine.wait_for_agent_tasks(),
                        timeout=15.0,
                    )

                except asyncio.TimeoutError:
                    await engine.cancel_agent_tasks()

                # =================================================
                # CLOSE PROVIDERS
                # =================================================
                await engine.close()

            # =====================================================
            # POST CALL
            #
            # Only finalize if the Twilio SID was successfully
            # resolved to a durable Call record.
            # =====================================================
            if call_sid and call_validated:
                POST_CALL_TOTAL.inc()

                post_call_started_at = time.perf_counter()

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

    finally:
        # =========================================================
        # CALL LIFECYCLE METRICS
        # =========================================================
        CALL_DURATION_SECONDS.observe(
            time.perf_counter() - call_started_at
        )

        CALLS_ACTIVE.dec()