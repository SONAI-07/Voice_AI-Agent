import json

from langgraph.graph import END, START, StateGraph
from app.agent.decision import AgentDecision, NextAction
from app.agent.prompt import SYSTEM_PROMPT
from app.agent.state import AgentState
from app.voice.sarvam_llm import SarvamLLM
from app.agent.analyze import analyze_signals
from app.agent.classification_node import classify_customer_node
from app.agent.action_node import determine_action_node
from app.agent.action_execution_node import execute_business_action

llm = SarvamLLM()


async def reason(state: AgentState) -> AgentState:
    conversation = state["conversation"]

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        *conversation,
        {
            "role": "user",
            "content": state["current_transcript"],
        },
    ]

    response_parts: list[str] = []

    async for chunk in SarvamLLM.generate_stream(messages):
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
            response_parts.append(text)

    raw_response = "".join(response_parts).strip()

    try:
        decision_data = json.loads(raw_response)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Sarvam returned invalid JSON: {raw_response}"
        ) from exc

    decision = AgentDecision.model_validate(decision_data)

    return {
        **state,
        "conversation": [
            *conversation,
            {
                "role": "user",
                "content": state["current_transcript"],
            },
            {
                "role": "assistant",
                "content": decision.response,
            },
        ],
        "agent_response": decision.response,
        "decision": decision,
    }


def route_decision(state: AgentState) -> str:
    decision = state["decision"]

    if decision is None:
        raise ValueError("Agent decision is missing from state")

    return decision.next_action.value


async def ask_question(state: AgentState) -> AgentState:
    decision = state["decision"]

    if decision is None:
        raise ValueError("Agent decision is missing from state")

    if decision.next_question is None:
        raise ValueError(
            "next_question is required for ask_question"
        )

    return {
        **state,
        "next_node": "ask_question",
    }


async def continue_conversation(state: AgentState) -> AgentState:
    return {
        **state,
        "next_node": "continue",
    }


async def end_conversation(state: AgentState) -> AgentState:
    return {
        **state,
        "next_node": "end_conversation",
    }


graph_builder = StateGraph(AgentState)

graph_builder.add_node("reason", reason)
graph_builder.add_node("ask_question", ask_question)
graph_builder.add_node("continue", continue_conversation)
graph_builder.add_node("end_conversation", end_conversation)
graph_builder.add_node("analyze_signals", analyze_signals)
graph_builder.add_node(
    "classify_customer",
    classify_customer_node,
)
graph_builder.add_node(
    "determine_action",
    determine_action_node,
)
graph_builder.add_node(
    "execute_business_action",
    execute_business_action,
)



graph_builder.add_edge(START, "reason")
graph_builder.add_edge("reason", "analyze_signals")
graph_builder.add_edge(
    "analyze_signals",
    "classify_customer",
)
graph_builder.add_edge(
    "classify_customer",
    "determine_action",
)
graph_builder.add_edge(
    "determine_action",
    "execute_business_action",
)


graph_builder.add_conditional_edges(
    "execute_business_action",
    route_decision,
    {
        NextAction.ASK_QUESTION.value: "ask_question",
        NextAction.CONTINUE.value: "continue",
        NextAction.END_CONVERSATION.value: "end_conversation",
    },
)


graph_builder.add_edge("ask_question", END)
graph_builder.add_edge("continue", END)
graph_builder.add_edge("end_conversation", END)

graph = graph_builder.compile()