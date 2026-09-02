import asyncio
import base64
import json
import time

import websockets
from websockets.asyncio.client import ClientConnection

from app.core.config import get_settings
from app.observability.metrics import (
    PROVIDER_ERRORS_TOTAL,
    PROVIDER_LATENCY_SECONDS,
    PROVIDER_REQUESTS_TOTAL,
    TIMEOUTS_TOTAL,
)
from app.voice.audio import mulaw_to_pcm16
from app.voice.stt import STTProvider


SARVAM_STT_CONNECT_TIMEOUT_SECONDS = 10.0
SARVAM_STT_SEND_TIMEOUT_SECONDS = 5.0


class SarvamSTT(STTProvider):

    def __init__(
            self,
            language_code: str = "en-IN",
    ) -> None:

        settings = get_settings()

        if not settings.sarvam_api_key:
            raise ValueError(
                "SARVAM_API_KEY is not configured"
            )

        self.api_key = settings.sarvam_api_key
        self.language_code = language_code

        self.websocket: ClientConnection | None = None

    # =============================================================
    # CONNECT
    # =============================================================

    async def connect(self) -> None:

        url = (
            "wss://api.sarvam.ai/speech-to-text/ws"
            "?model=saaras:v3"
            f"&language-code={self.language_code}"
            "&mode=transcribe"
            "&sample-rate=8000"
            "&input-audio-codec=pcm_s16le"
            "&high-vad-sensitivity=true"
            "&vad-signals=true"
        )

        PROVIDER_REQUESTS_TOTAL.labels(
            provider="sarvam_stt",
            operation="connect",
        ).inc()

        started_at = time.perf_counter()

        try:

            self.websocket = await asyncio.wait_for(
                websockets.connect(
                    url,
                    additional_headers={
                        "api-subscription-key": (
                            self.api_key
                        ),
                    },
                    open_timeout=(
                        SARVAM_STT_CONNECT_TIMEOUT_SECONDS
                    ),
                    close_timeout=5,
                    ping_interval=20,
                    ping_timeout=10,
                ),
                timeout=(
                        SARVAM_STT_CONNECT_TIMEOUT_SECONDS
                        + 2
                ),
            )

            PROVIDER_LATENCY_SECONDS.labels(
                provider="sarvam_stt",
                operation="connect",
            ).observe(
                time.perf_counter()
                - started_at
            )

        except asyncio.TimeoutError as exc:

            TIMEOUTS_TOTAL.labels(
                provider="sarvam_stt",
                operation="connect",
            ).inc()

            PROVIDER_ERRORS_TOTAL.labels(
                provider="sarvam_stt",
                operation="connect",
                error_type="TimeoutError",
            ).inc()

            raise

        except asyncio.CancelledError:
            raise

        except Exception as exc:

            PROVIDER_ERRORS_TOTAL.labels(
                provider="sarvam_stt",
                operation="connect",
                error_type=type(exc).__name__,
            ).inc()

            raise

    # =============================================================
    # SEND AUDIO
    # =============================================================

    async def send_audio(
            self,
            audio: bytes,
    ) -> None:

        if self.websocket is None:
            raise RuntimeError(
                "Sarvam STT is not connected"
            )

        pcm_audio = mulaw_to_pcm16(
            audio
        )

        message = {
            "audio": {
                "data": (
                    base64.b64encode(
                        pcm_audio
                    ).decode("utf-8")
                ),
                "sample_rate": 8000,
                "encoding": "pcm_s16le",
            }
        }

        PROVIDER_REQUESTS_TOTAL.labels(
            provider="sarvam_stt",
            operation="send_audio",
        ).inc()

        started_at = time.perf_counter()

        try:

            await asyncio.wait_for(
                self.websocket.send(
                    json.dumps(message)
                ),
                timeout=(
                    SARVAM_STT_SEND_TIMEOUT_SECONDS
                ),
            )

            PROVIDER_LATENCY_SECONDS.labels(
                provider="sarvam_stt",
                operation="send_audio",
            ).observe(
                time.perf_counter()
                - started_at
            )

        except asyncio.TimeoutError:

            TIMEOUTS_TOTAL.labels(
                provider="sarvam_stt",
                operation="send_audio",
            ).inc()

            raise

        except asyncio.CancelledError:
            raise

        except Exception as exc:

            PROVIDER_ERRORS_TOTAL.labels(
                provider="sarvam_stt",
                operation="send_audio",
                error_type=type(exc).__name__,
            ).inc()

            raise

    # =============================================================
    # RECEIVE EVENTS
    # =============================================================

    async def receive_events(self):

        if self.websocket is None:
            raise RuntimeError(
                "Sarvam STT is not connected"
            )

        try:

            async for raw_message in self.websocket:

                yield json.loads(
                    raw_message
                )

        except asyncio.CancelledError:

            raise

        except Exception as exc:

            PROVIDER_ERRORS_TOTAL.labels(
                provider="sarvam_stt",
                operation="receive_events",
                error_type=type(exc).__name__,
            ).inc()

            raise

    # =============================================================
    # CLOSE
    # =============================================================

    async def close(self) -> None:

        if self.websocket is None:
            return

        websocket = self.websocket
        self.websocket = None

        try:

            await websocket.close()

        except Exception as exc:

            PROVIDER_ERRORS_TOTAL.labels(
                provider="sarvam_stt",
                operation="close",
                error_type=type(exc).__name__,
            ).inc()