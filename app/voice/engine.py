import asyncio
from typing import TypedDict

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
        # Agent turn lifecycle
        # ---------------------------------------------------------

        self._turn_queue: asyncio.Queue[
            AgentTurn | None
            ] = asyncio.Queue()

        self._worker_task: asyncio.Task | None = None

        # The currently executing LangGraph/agent turn.
        self.tts_task: asyncio.Task | None = None

        # Persistent state for the current call.
        #
        # This is what allows intent_history and
        # live_action_triggered to survive between turns.
        self._agent_state = None

    # -------------------------------------------------------------
    # Call lifecycle
    # -------------------------------------------------------------

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

        # Start exactly ONE agent worker.
        self._worker_task = asyncio.create_task(
            self._agent_worker()
        )

    # -------------------------------------------------------------
    # STT
    # -------------------------------------------------------------

    async def receive_stt_events(self):

        async for event in self.stt.receive_events():
            yield event

    # -------------------------------------------------------------
    # Transcript submission
    # -------------------------------------------------------------

    async def submit_transcript(
            self,
            transcript: str,
    ) -> None:

        if not self.call_sid:
            raise RuntimeError(
                "call_sid must be set before "
                "processing transcripts"
            )

        transcript = transcript.strip()

        if not transcript:
            return

        # IMPORTANT:
        #
        # The WebSocket has already written the user message
        # into Redis.
        #
        # We capture the conversation NOW so that Turn A gets
        # Turn A's snapshot and Turn B gets Turn B's snapshot.
        #
        # Without this, Turn A might execute after Turn B has
        # already been written to Redis.
        conversation = await self.memory.get_messages(
            self.call_sid
        )

        await self._turn_queue.put(
            {
                "transcript": transcript,
                "conversation": conversation,
            }
        )

    # -------------------------------------------------------------
    # Sequential agent worker
    # -------------------------------------------------------------

    async def _agent_worker(self) -> None:

        while True:

            turn = await self._turn_queue.get()

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

                # Interruption is an expected event in a
                # real-time voice conversation.
                pass

            finally:

                self.tts_task = None
                self._turn_queue.task_done()

    # -------------------------------------------------------------
    # Agent turn
    # -------------------------------------------------------------

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

        # Import lazily so the voice engine does not participate
        # in application import cycles.
        from app.agent.graph import graph

        # ---------------------------------------------------------
        # Create persistent state for the FIRST turn.
        # ---------------------------------------------------------

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

        else:

            # -----------------------------------------------------
            # Preserve cross-turn agent state.
            #
            # In particular:
            #
            # intent_history
            # live_action_triggered
            #
            # must NOT reset on every turn.
            # -----------------------------------------------------

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

        # ---------------------------------------------------------
        # Execute LangGraph.
        # ---------------------------------------------------------

        final_state = await graph.ainvoke(
            self._agent_state
        )

        # Persist state for the next turn.
        self._agent_state = final_state

        assistant_response = (
            final_state["agent_response"]
        )

        if not assistant_response:
            return

        # ---------------------------------------------------------
        # Persist assistant response.
        # ---------------------------------------------------------

        await self.memory.append_message(
            call_sid=self.call_sid,
            role="assistant",
            content=assistant_response,
        )

        # ---------------------------------------------------------
        # Send response through TTS.
        # ---------------------------------------------------------

        await self.tts.synthesize(
            assistant_response
        )

    # -------------------------------------------------------------
    # Wait for all accepted agent work
    # -------------------------------------------------------------

    async def wait_for_agent_tasks(
            self,
    ) -> None:

        # Wait until every submitted turn has called task_done().
        #
        # This includes queued turns and the currently executing
        # turn.
        await self._turn_queue.join()

    # -------------------------------------------------------------
    # Interrupt current agent turn
    # -------------------------------------------------------------

    async def interrupt(self) -> None:

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

        await self.tts.clear()

        self.tts_task = None

    # -------------------------------------------------------------
    # Cancel everything
    # -------------------------------------------------------------

    async def cancel_agent_tasks(
            self,
    ) -> None:

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

        # Stop the worker itself.
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

        # Clear any turns which could not be processed.
        while not self._turn_queue.empty():

            try:
                self._turn_queue.get_nowait()
                self._turn_queue.task_done()

            except asyncio.QueueEmpty:
                break

    # -------------------------------------------------------------
    # Shutdown
    # -------------------------------------------------------------

    async def close(self) -> None:

        self.running = False

        # The caller should normally call
        # wait_for_agent_tasks() BEFORE close().
        #
        # This method is the final hard shutdown safeguard.

        if self._worker_task is not None:

            self._worker_task.cancel()

            try:
                await self._worker_task

            except asyncio.CancelledError:
                pass

        await self.tts.clear()

        await self.stt.close()
        await self.tts.close()

        self.tts_task = None
        self._worker_task = None
        self._agent_state = None