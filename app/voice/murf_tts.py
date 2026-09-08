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
from app.voice.tts import TTSProvider


MURF_TTS_CONNECT_TIMEOUT_SECONDS = 10.0
MURF_TTS_SEND_TIMEOUT_SECONDS = 5.0


class MurfTTS(TTSProvider):

    def __init__(self) -> None:

        settings = get_settings()

        if not settings.murf_api_key:
            raise ValueError(
                "MURF_API_KEY is not configured"
            )

        if not settings.murf_voice_id:
            raise ValueError(
                "MURF_VOICE_ID is not configured"
            )

        self.api_key = settings.murf_api_key
        self.voice_id = settings.murf_voice_id

        self.websocket: ClientConnection | None = None

    # =============================================================
    # CONNECT
    # =============================================================

    async def connect(self) -> None:

        url = (
            "wss://in.api.murf.ai/v1/speech/stream-input"
            "?model=falcon-2"
            "&sample_rate=8000"
            "&channel_type=MONO"
            "&format=ULAW"
        )

        PROVIDER_REQUESTS_TOTAL.labels(
            provider="murf_tts",
            operation="connect",
        ).inc()

        started_at = time.perf_counter()

        try:

            self.websocket = await asyncio.wait_for(
                websockets.connect(
                    url,
                    additional_headers={
                        "api_key": self.api_key,
                    },
                    open_timeout=(
                        MURF_TTS_CONNECT_TIMEOUT_SECONDS
                    ),
                    close_timeout=5,
                    ping_interval=20,
                    ping_timeout=10,
                ),
                timeout=(
                        MURF_TTS_CONNECT_TIMEOUT_SECONDS + 2
                ),
            )

            await asyncio.wait_for(
                self.websocket.send(
                    json.dumps(
                        {
                            "voice_config": {
                                "voice_id": self.voice_id,
                                "language": "en-US",
                            }
                        }
                    )
                ),
                timeout=MURF_TTS_SEND_TIMEOUT_SECONDS,
            )

            PROVIDER_LATENCY_SECONDS.labels(
                provider="murf_tts",
                operation="connect",
            ).observe(
                time.perf_counter() - started_at
            )

        except asyncio.TimeoutError:

            TIMEOUTS_TOTAL.labels(
                provider="murf_tts",
                operation="connect",
            ).inc()

            PROVIDER_ERRORS_TOTAL.labels(
                provider="murf_tts",
                operation="connect",
                error_type="TimeoutError",
            ).inc()

            raise

        except asyncio.CancelledError:

            raise

        except Exception as exc:

            PROVIDER_ERRORS_TOTAL.labels(
                provider="murf_tts",
                operation="connect",
                error_type=type(exc).__name__,
            ).inc()

            raise

    # =============================================================
    # SYNTHESIZE
    # =============================================================

    async def synthesize(
            self,
            text: str,
    ) -> None:

        if self.websocket is None:
            raise RuntimeError(
                "Murf TTS is not connected"
            )

        if not text.strip():
            return

        PROVIDER_REQUESTS_TOTAL.labels(
            provider="murf_tts",
            operation="synthesize",
        ).inc()

        started_at = time.perf_counter()

        try:

            await asyncio.wait_for(
                self.websocket.send(
                    json.dumps(
                        {
                            "sendText": {
                                "text": text,
                            }
                        }
                    )
                ),
                timeout=MURF_TTS_SEND_TIMEOUT_SECONDS,
            )

            PROVIDER_LATENCY_SECONDS.labels(
                provider="murf_tts",
                operation="synthesize",
            ).observe(
                time.perf_counter() - started_at
            )

        except asyncio.TimeoutError:

            TIMEOUTS_TOTAL.labels(
                provider="murf_tts",
                operation="synthesize",
            ).inc()

            PROVIDER_ERRORS_TOTAL.labels(
                provider="murf_tts",
                operation="synthesize",
                error_type="TimeoutError",
            ).inc()

            raise

        except asyncio.CancelledError:

            raise

        except Exception as exc:

            PROVIDER_ERRORS_TOTAL.labels(
                provider="murf_tts",
                operation="synthesize",
                error_type=type(exc).__name__,
            ).inc()

            raise

    # =============================================================
    # RECEIVE AUDIO
    # =============================================================

    async def receive_audio(self):

        if self.websocket is None:
            raise RuntimeError(
                "Murf TTS is not connected"
            )

        PROVIDER_REQUESTS_TOTAL.labels(
            provider="murf_tts",
            operation="receive_audio",
        ).inc()

        started_at = time.perf_counter()

        try:

            async for raw_message in self.websocket:

                message = json.loads(
                    raw_message
                )

                if "audioOutput" in message:

                    audio = (
                        message["audioOutput"]
                        .get("audio")
                    )

                    if audio:

                        yield base64.b64decode(
                            audio
                        )

                elif "finalOutput" in message:

                    PROVIDER_LATENCY_SECONDS.labels(
                        provider="murf_tts",
                        operation="receive_audio",
                    ).observe(
                        time.perf_counter()
                        - started_at
                    )

                    break

        except asyncio.CancelledError:

            raise

        except Exception as exc:

            PROVIDER_ERRORS_TOTAL.labels(
                provider="murf_tts",
                operation="receive_audio",
                error_type=type(exc).__name__,
            ).inc()

            raise

    # =============================================================
    # CLEAR CONTEXT
    # =============================================================

    async def clear(self) -> None:

        if self.websocket is None:
            return

        PROVIDER_REQUESTS_TOTAL.labels(
            provider="murf_tts",
            operation="clear",
        ).inc()

        started_at = time.perf_counter()

        try:

            await asyncio.wait_for(
                self.websocket.send(
                    json.dumps(
                        {
                            "clearContext": {},
                        }
                    )
                ),
                timeout=MURF_TTS_SEND_TIMEOUT_SECONDS,
            )

            PROVIDER_LATENCY_SECONDS.labels(
                provider="murf_tts",
                operation="clear",
            ).observe(
                time.perf_counter() - started_at
            )

        except asyncio.TimeoutError:

            TIMEOUTS_TOTAL.labels(
                provider="murf_tts",
                operation="clear",
            ).inc()

            PROVIDER_ERRORS_TOTAL.labels(
                provider="murf_tts",
                operation="clear",
                error_type="TimeoutError",
            ).inc()

            raise

        except asyncio.CancelledError:

            raise

        except Exception as exc:

            PROVIDER_ERRORS_TOTAL.labels(
                provider="murf_tts",
                operation="clear",
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

        PROVIDER_REQUESTS_TOTAL.labels(
            provider="murf_tts",
            operation="close",
        ).inc()

        started_at = time.perf_counter()

        try:

            await websocket.close()

            PROVIDER_LATENCY_SECONDS.labels(
                provider="murf_tts",
                operation="close",
            ).observe(
                time.perf_counter() - started_at
            )

        except asyncio.CancelledError:

            raise

        except Exception as exc:

            PROVIDER_ERRORS_TOTAL.labels(
                provider="murf_tts",
                operation="close",
                error_type=type(exc).__name__,
            ).inc()

            raise

