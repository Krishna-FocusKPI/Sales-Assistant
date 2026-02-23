"""
MPR LangGraph: agent node + ToolNode, same pattern as PPR. Three tools only.
"""
from typing import Literal

from langchain_core.messages import AIMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from src.common.provider import get_chat_model

from .mpr_prompts import MPR_SYSTEM_PROMPT
from .mpr_state import MPRState
from .mpr_tools import get_mpr_tools


def _agent_node(state: MPRState, *, provider: Literal["openai", "anthropic"] = "openai") -> dict:
    messages = list(state.get("messages") or [])
    system = SystemMessage(content=MPR_SYSTEM_PROMPT)
    model = get_chat_model(provider).bind_tools(get_mpr_tools())
    response = model.invoke([system] + messages)
    return {"messages": [response]}


def _should_continue(state: MPRState) -> Literal["tools", "__end__"]:
    messages = state.get("messages") or []
    if not messages:
        return "__end__"
    last = messages[-1]
    if isinstance(last, AIMessage) and getattr(last, "tool_calls", None):
        return "tools"
    return "__end__"


def build_mpr_graph(provider: Literal["openai", "anthropic"] = "openai"):
    graph = StateGraph(MPRState)
    tool_node = ToolNode(get_mpr_tools())
    graph.add_node("agent", lambda s: _agent_node(s, provider=provider))
    graph.add_node("tools", tool_node)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", _should_continue, {"tools": "tools", "__end__": END})
    graph.add_edge("tools", "agent")
    return graph.compile()
