import base64
import json

import websockets

from app.core.config import get_settings
from app.voice.tts import TTSProvider


class MurfTTS(TTSProvider):

    def __init__(self) -> None:
        settings = get_settings()

        self.api_key = settings.murf_api_key
        self.voice_id = settings.murf_voice_id
        self.websocket = None

    async def connect(self) -> None:
        url = (
            "wss://in.api.murf.ai/v1/speech/stream-input"
            "?model=falcon-2"
            "&sample_rate=8000"
            "&channel_type=MONO"
            "&format=ULAW"
        )

        self.websocket = await websockets.connect(
            url,
            additional_headers={
                "api_key": self.api_key,
            },
        )

        await self.websocket.send(
            json.dumps(
                {
                    "voice_config": {
                        "voice_id": self.voice_id,
                        "language": "en-US",
                    }
                }
            )
        )

    async def synthesize(self, text: str) -> None:
        await self.websocket.send(
            json.dumps(
                {
                    "sendText": {
                        "text": text,
                    }
                }
            )
        )

    async def receive_audio(self):
        async for raw_message in self.websocket:
            message = json.loads(raw_message)

            if "audioOutput" in message:
                audio = message["audioOutput"].get("audio")

                if audio:
                    yield base64.b64decode(audio)

            elif "finalOutput" in message:
                break

    async def clear(self) -> None:
        await self.websocket.send(
            json.dumps(
                {
                    "clearContext": {},
                }
            )
        )

    async def close(self) -> None:
        if self.websocket:
            await self.websocket.close()