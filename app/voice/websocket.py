import asyncio
import base64

from fastapi import (
    APIRouter,
    WebSocket,
    WebSocketDisconnect,
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

    # -------------------------------------------------------------
    # Services
    # -------------------------------------------------------------

    memory = CallMemory()

    post_call_service = PostCallService(
        memory=memory
    )

    call_sid: str | None = None

    # -------------------------------------------------------------
    # Voice engine
    # -------------------------------------------------------------

    engine = RealtimeVoiceEngine(
        stt=SarvamSTT(
            language_code="en-IN"
        ),
        llm=SarvamLLM(),
        tts=MurfTTS(),
        memory=memory,
    )

    await engine.start()

    # -------------------------------------------------------------
    # Twilio → STT
    # -------------------------------------------------------------

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

                # -------------------------------------------------
                # START
                # -------------------------------------------------

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

                # -------------------------------------------------
                # MEDIA
                # -------------------------------------------------

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

                # -------------------------------------------------
                # STOP
                # -------------------------------------------------

                elif event == "stop":

                    break

        except WebSocketDisconnect:

            pass

    # -------------------------------------------------------------
    # STT → Agent
    # -------------------------------------------------------------

    async def process_stt():

        async for event in (
                engine.receive_stt_events()
        ):

            event_type = event.get(
                "type"
            )

            # -----------------------------------------------------
            # CUSTOMER STARTED SPEAKING
            # -----------------------------------------------------

            if event_type == "speech_start":

                await engine.interrupt()

            # -----------------------------------------------------
            # FINAL TRANSCRIPT
            # -----------------------------------------------------

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

                # -------------------------------------------------
                # USER MESSAGE → REDIS
                # -------------------------------------------------

                await memory.append_message(
                    call_sid=call_sid,
                    role="user",
                    content=transcript,
                )

                # -------------------------------------------------
                # Submit to sequential agent worker.
                # -------------------------------------------------

                await engine.submit_transcript(
                    transcript
                )

    # -------------------------------------------------------------
    # TTS → Twilio
    # -------------------------------------------------------------

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

    # -------------------------------------------------------------
    # Create independent lifecycle tasks
    # -------------------------------------------------------------

    receive_task = asyncio.create_task(
        receive_twilio_audio()
    )

    stt_task = asyncio.create_task(
        process_stt()
    )

    tts_audio_task = asyncio.create_task(
        send_tts_audio()
    )

    # -------------------------------------------------------------
    # CALL LIFECYCLE
    # -------------------------------------------------------------

    try:

        # The Twilio receiver is the authoritative
        # lifecycle controller.
        await receive_task

    except WebSocketDisconnect:

        pass

    finally:

        # =========================================================
        # STEP 1
        # Stop accepting STT events.
        # =========================================================

        stt_task.cancel()

        try:

            await stt_task

        except asyncio.CancelledError:

            pass

        # =========================================================
        # STEP 2
        # Stop forwarding new TTS audio to Twilio.
        # =========================================================

        tts_audio_task.cancel()

        try:

            await tts_audio_task

        except asyncio.CancelledError:

            pass

        # =========================================================
        # STEP 3
        # Wait for ALL accepted agent turns.
        #
        # This is the exact location where the previously
        # confusing wait_for_agent_tasks() belongs.
        # =========================================================

        try:

            await asyncio.wait_for(
                engine.wait_for_agent_tasks(),
                timeout=15.0,
            )

        except asyncio.TimeoutError:

            # A broken/hung LLM/TTS operation must not keep
            # the call lifecycle open indefinitely.
            await engine.cancel_agent_tasks()

        # =========================================================
        # STEP 4
        # Close voice providers.
        # =========================================================

        await engine.close()

        # =========================================================
        # STEP 5
        # Durable post-call processing.
        #
        # Redis MUST NOT be deleted if this fails.
        # =========================================================

        if call_sid:

            try:

                await post_call_service.finalize_call(
                    call_sid
                )

            except Exception:

                # IMPORTANT:
                #
                # Do NOT call memory.delete() here.
                #
                # PostCallService controls Redis deletion and
                # only does so after successful durable processing.
                raise