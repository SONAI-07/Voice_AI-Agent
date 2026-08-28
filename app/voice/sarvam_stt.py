import base64
import json

import websockets

from app.core.config import get_settings
from app.voice.audio import mulaw_to_pcm16
from app.voice.stt import STTProvider


class SarvamSTT(STTProvider):

    def __init__(
            self,
            language_code: str = "en-IN",
    ) -> None:
        settings = get_settings()

        self.api_key = settings.sarvam_api_key
        self.language_code = language_code
        self.websocket = None

    async def connect(self) -> None:
        url = (
            "wss://api.sarvam.ai/speech-to-text/ws"
            f"?model=saaras:v3"
            f"&language-code={self.language_code}"
            f"&mode=transcribe"
            f"&sample-rate=8000"
            f"&input-audio-codec=pcm_s16le"
            f"&high-vad-sensitivity=true"
            f"&vad-signals=true"
        )

        self.websocket = await websockets.connect(
            url,
            additional_headers={
                "api-subscription-key": self.api_key,
            },
        )

    async def send_audio(self, audio: bytes) -> None:
        pcm_audio = mulaw_to_pcm16(audio)

        message = {
            "audio": {
                "data": base64.b64encode(pcm_audio).decode("utf-8"),
                "sample_rate": 8000,
                "encoding": "pcm_s16le",
            }
        }

        await self.websocket.send(json.dumps(message))

    async def receive_events(self):
        async for raw_message in self.websocket:
            yield json.loads(raw_message)

    async def close(self) -> None:
        if self.websocket:
            await self.websocket.close()