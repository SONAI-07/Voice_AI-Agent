import asyncio
import json

from app.agent.graph import graph
from app.services.call_memory import CallMemory

from .llm import LLMProvider
from .stt import STTProvider
from .tts import TTSProvider


class RealtimeVoiceEngine:

    def __init__(
            self,
            stt: STTProvider,
            llm: LLMProvider,
            tts: TTSProvider,
            memory: CallMemory,
    ) -> None:
        self.stt = stt
        self.llm = llm
        self.tts = tts
        self.memory = memory

        self.call_sid: str | None = None

        self.running = False
        self.tts_task: asyncio.Task | None = None

    def set_call_sid(self, call_sid: str) -> None:
        if not call_sid:
            raise ValueError("call_sid is required")

        self.call_sid = call_sid

    async def start(self) -> None:
        await self.stt.connect()
        await self.tts.connect()

        self.running = True

    async def receive_stt_events(self):
        async for event in self.stt.receive_events():
            yield event

    async def process_transcript(
            self,
            transcript: str,
    ) -> None:

        if not self.call_sid:
            raise RuntimeError(
                "call_sid must be set before processing transcripts"
            )

        if not transcript.strip():
            return

        # The WebSocket is responsible for appending the finalized
        # user transcript to Redis before calling this method.
        conversation = await self.memory.get_messages(
            self.call_sid
        )

        initial_state = {
            "call_sid": self.call_sid,
            "conversation": conversation,
            "current_transcript": transcript,
            "agent_response": "",
            "decision": None,
            "next_node": None,
            "intent": None,
            "emotion": None,
            "classification": None,
            "action": None,
            "action_executed": False,
        }

        final_state = await graph.ainvoke(initial_state)

        assistant_response = final_state["agent_response"]

        if not assistant_response:
            return

        await self.memory.append_message(
            call_sid=self.call_sid,
            role="assistant",
            content=assistant_response,
        )

        await self.tts.synthesize(assistant_response)

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