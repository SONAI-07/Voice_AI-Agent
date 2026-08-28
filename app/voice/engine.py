import asyncio
import json

from .llm import LLMProvider
from .stt import STTProvider
from .tts import TTSProvider
from sarvam_llm import SarvamLLM


class RealtimeVoiceEngine:

    def __init__(
            self,
            stt: STTProvider,
            llm: SarvamLLM,
            tts: TTSProvider,
    ) -> None:
        self.stt = stt
        self.llm = llm
        self.tts = tts

        self.running = False
        self.tts_task: asyncio.Task | None = None

    async def start(self) -> None:
        await self.stt.connect()
        await self.tts.connect()

        self.running = True

    async def receive_stt_events(self):
        async for event in self.stt.receive_events():
            yield event

    async def process_transcript(self, transcript: str) -> None:
        async for chunk in self.llm.generate_stream(transcript):
            try:
                data = json.loads(chunk)
            except json.JSONDecodeError:
                continue

            choices = data.get("choices", [])

            if not choices:
                continue

            delta = choices[0].get("delta", {})
            text = delta.get("content")

            if text:
                await self.tts.synthesize(text)

    async def interrupt(self) -> None:
        if self.tts_task and not self.tts_task.done():
            self.tts_task.cancel()

        await self.tts.clear()

    async def close(self) -> None:
        self.running = False

        if self.tts_task and not self.tts_task.done():
            self.tts_task.cancel()

        await self.stt.close()
        await self.tts.close()