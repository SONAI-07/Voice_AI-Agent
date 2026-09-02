import asyncio
import time
from typing import TypedDict

from app.observability.metrics import (
    AGENT_INTERRUPTS_TOTAL,
    AGENT_QUEUE_DEPTH,
    AGENT_TURN_ERRORS_TOTAL,
    AGENT_TURN_LATENCY_SECONDS,
    AGENT_TURNS_TOTAL,
    TTS_ERRORS_TOTAL,
    TTS_LATENCY_SECONDS,
    TTS_REQUESTS_TOTAL,
)
from app.services.call_memory import CallMemory

from .llm import LLMProvider
from .stt import STTProvider
from .tts import TTSProvider


class AgentTurn(TypedDict):
    transcript: str
    conversation: list[dict[str, str]]


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

        # ---------------------------------------------------------
        # Agent queue
        # ---------------------------------------------------------

        self._turn_queue: asyncio.Queue[
            AgentTurn | None
            ] = asyncio.Queue()

        self._worker_task: asyncio.Task | None = None

        # Current LangGraph / TTS task.
        self.tts_task: asyncio.Task | None = None

        # Persistent state across turns.
        self._agent_state = None

    # =============================================================
    # CALL LIFECYCLE
    # =============================================================

    def set_call_sid(
            self,
            call_sid: str,
    ) -> None:

        if not call_sid:
            raise ValueError(
                "call_sid is required"
            )

        self.call_sid = call_sid

    async def start(self) -> None:

        await self.stt.connect()
        await self.tts.connect()

        self.running = True

        self._worker_task = asyncio.create_task(
            self._agent_worker()
        )

    # =============================================================
    # STT
    # =============================================================

    async def receive_stt_events(self):

        async for event in self.stt.receive_events():

            yield event

    # =============================================================
    # SUBMIT TRANSCRIPT
    # =============================================================

    async def submit_transcript(self,transcript: str,) -> None:

        if not self.call_sid:
            raise RuntimeError(
                "call_sid must be set before "
                "processing transcripts"
            )

        transcript = transcript.strip()

        if not transcript:
            return

        conversation = (
            await self.memory.get_messages(
                self.call_sid
            )
        )

        await self._turn_queue.put(
            {
                "transcript": transcript,
                "conversation": conversation,
            }
        )

        AGENT_QUEUE_DEPTH.set(
            self._turn_queue.qsize()
        )

    # =============================================================
    # SEQUENTIAL AGENT WORKER
    # =============================================================

    async def _agent_worker(self) -> None:

        while True:

            turn = await self._turn_queue.get()

            AGENT_QUEUE_DEPTH.set(
                self._turn_queue.qsize()
            )

            if turn is None:

                self._turn_queue.task_done()

                break

            transcript = turn["transcript"]
            conversation = turn["conversation"]

            task = asyncio.create_task(
                self.process_transcript(
                    transcript=transcript,
                    conversation=conversation,
                )
            )

            self.tts_task = task

            try:

                await task

            except asyncio.CancelledError:

                # Customer interruption is expected in
                # real-time voice interaction.
                pass

            except Exception as exc:

                AGENT_TURN_ERRORS_TOTAL.labels(
                    environment="production",
                    error_type=type(exc).__name__,
                ).inc()

                raise

            finally:

                self.tts_task = None

                self._turn_queue.task_done()

                AGENT_QUEUE_DEPTH.set(
                    self._turn_queue.qsize()
                )

    # =============================================================
    # AGENT TURN
    # =============================================================

    async def process_transcript(
            self,
            transcript: str,
            conversation: list[dict[str, str]],
    ) -> None:

        if not self.call_sid:
            raise RuntimeError(
                "call_sid must be set before "
                "processing transcripts"
            )

        if not transcript.strip():
            return

        start_time = time.perf_counter()

        AGENT_TURNS_TOTAL.labels(
            environment="production"
        ).inc()

        try:

            from app.agent.graph import graph

            # -----------------------------------------------------
            # INITIAL STATE
            # -----------------------------------------------------

            if self._agent_state is None:

                self._agent_state = {
                    "call_sid": self.call_sid,
                    "conversation": conversation,
                    "current_transcript": transcript,
                    "agent_response": "",

                    "decision": None,
                    "next_node": None,

                    "intent": None,
                    "emotion": None,
                    "classification": None,

                    "intent_history": [],

                    "explicit_positive_signal": False,
                    "sustained_high_intent": False,
                    "live_action_triggered": False,

                    "action": None,
                    "action_executed": False,
                }

            # -----------------------------------------------------
            # SUBSEQUENT STATE
            # -----------------------------------------------------

            else:

                self._agent_state = {
                    **self._agent_state,

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

            # -----------------------------------------------------
            # LANGGRAPH
            # -----------------------------------------------------

            final_state = await graph.ainvoke(
                self._agent_state
            )

            self._agent_state = final_state

            assistant_response = (
                final_state["agent_response"]
            )

            if not assistant_response:
                return

            # -----------------------------------------------------
            # REDIS
            # -----------------------------------------------------

            await self.memory.append_message(
                call_sid=self.call_sid,
                role="assistant",
                content=assistant_response,
            )

            # -----------------------------------------------------
            # TTS
            # -----------------------------------------------------

            TTS_REQUESTS_TOTAL.inc()

            tts_start = time.perf_counter()

            try:

                await self.tts.synthesize(
                    assistant_response
                )

            except Exception as exc:

                TTS_ERRORS_TOTAL.labels(
                    error_type=type(exc).__name__,
                ).inc()

                raise

            finally:

                TTS_LATENCY_SECONDS.observe(
                    time.perf_counter()
                    - tts_start
                )

        except asyncio.CancelledError:

            raise

        except Exception as exc:

            AGENT_TURN_ERRORS_TOTAL.labels(
                environment="production",
                error_type=type(exc).__name__,
            ).inc()

            raise

        finally:

            AGENT_TURN_LATENCY_SECONDS.observe(
                time.perf_counter()
                - start_time
            )

    # =============================================================
    # WAIT FOR AGENT WORK
    # =============================================================

    async def wait_for_agent_tasks(
            self,
    ) -> None:

        await self._turn_queue.join()

    # =============================================================
    # INTERRUPTION
    # =============================================================

    async def interrupt(self) -> None:

        current_task = self.tts_task

        if (
                current_task is not None
                and not current_task.done()
        ):

            AGENT_INTERRUPTS_TOTAL.inc()

            current_task.cancel()

            try:

                await current_task

            except asyncio.CancelledError:

                pass

        await self.tts.clear()

        self.tts_task = None

    # =============================================================
    # HARD CANCEL
    # =============================================================

    async def cancel_agent_tasks(self) -> None:

        current_task = self.tts_task

        if (
                current_task is not None
                and not current_task.done()
        ):

            current_task.cancel()

            try:

                await current_task

            except asyncio.CancelledError:

                pass

        if (
                self._worker_task is not None
                and not self._worker_task.done()
        ):

            self._worker_task.cancel()

            try:

                await self._worker_task

            except asyncio.CancelledError:

                pass

        self.tts_task = None
        self._worker_task = None

        # Drain unprocessed queue items.
        while not self._turn_queue.empty():

            try:

                self._turn_queue.get_nowait()

                self._turn_queue.task_done()

            except asyncio.QueueEmpty:

                break

        AGENT_QUEUE_DEPTH.set(0)

    # =============================================================
    # CLOSE
    # =============================================================

    async def close(self) -> None:

        self.running = False

        await self.tts.clear()

        await self.stt.close()
        await self.tts.close()

        self.tts_task = None
        self._worker_task = None
        self._agent_state = None

        AGENT_QUEUE_DEPTH.set(0)