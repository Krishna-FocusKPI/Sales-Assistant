"""
IPR LangGraph: agent node + ToolNode, conditional edge to tools or END.
Tools may run in a worker thread; we set workflow from config so they can read it.
"""
from typing import Literal

from langchain_core.messages import AIMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from src.common.provider import get_chat_model

from .ipr_prompts import IPR_SYSTEM_PROMPT
from .ipr_state import IPRState
from .ipr_tools import get_ipr_tools


def _agent_node(state: IPRState, *, provider: Literal["openai", "anthropic"] = "openai") -> dict:
    """Run the model on messages; return new messages (AIMessage, possibly with tool_calls)."""
    messages = list(state.get("messages") or [])
    system = SystemMessage(content=IPR_SYSTEM_PROMPT)
    model = get_chat_model(provider).bind_tools(get_ipr_tools())
    response = model.invoke([system] + messages)
    return {"messages": [response]}


def _should_continue(state: IPRState) -> Literal["tools", "__end__"]:
    """If the last message has tool_calls, go to tools; else END."""
    messages = state.get("messages") or []
    if not messages:
        return "__end__"
    last = messages[-1]
    if isinstance(last, AIMessage) and getattr(last, "tool_calls", None):
        return "tools"
    return "__end__"


def build_ipr_graph(provider: Literal["openai", "anthropic"] = "openai"):
    """Build and compile the IPR LangGraph. Returns a compiled graph."""
    graph = StateGraph(IPRState)
    tool_node = ToolNode(get_ipr_tools())

    graph.add_node("agent", lambda s: _agent_node(s, provider=provider))
    graph.add_node("tools", tool_node)

    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", _should_continue, {"tools": "tools", "__end__": END})
    graph.add_edge("tools", "agent")

    return graph.compile()
