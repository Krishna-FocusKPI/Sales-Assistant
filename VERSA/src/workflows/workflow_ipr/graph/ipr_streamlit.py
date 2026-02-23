"""
Wire IPR LangGraph to Streamlit. Graph state = messages only. Tools use
st.session_state.workflow['workflow_memory'] for context (set by init_ipr_workflow).
"""
import logging

import streamlit as st
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage

from .ipr_graph import build_ipr_graph
from .ipr_state import IPRState

GREEN = "\033[32m"
RESET = "\033[0m"


def _tool_activity_from_messages(messages: list, start_index: int) -> list[str]:
    """Collect tool names used in this turn (messages from start_index onward)."""
    activity = []
    for m in messages[start_index:]:
        if isinstance(m, AIMessage) and getattr(m, "tool_calls", None):
            for tc in m.tool_calls or []:
                name = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", None)
                if name:
                    activity.append(name)
        if isinstance(m, ToolMessage):
            name = getattr(m, "name", None)
            if name and (not activity or activity[-1] != name):
                activity.append(name)
    return activity


def _session_messages_to_lc(session_messages: list[dict]) -> list[BaseMessage]:
    """Convert st.session_state.messages (role/content) to LangChain BaseMessage list."""
    out = []
    for m in session_messages:
        role = (m.get("role") or "").strip().lower()
        content = m.get("content") or ""
        if role == "human":
            out.append(HumanMessage(content=content))
        else:
            out.append(AIMessage(content=content))
    return out


def run_ipr_turn(user_message: str, *, provider: str = "openai") -> None:
    """
    Run one IPR LangGraph turn. State = messages only. Tools read/write
    st.session_state.workflow['workflow_memory'] (already set by init_ipr_workflow).
    Pass workflow in config so tools can access it when running in a worker thread.
    """
    logging.info("%sUsing provider: %s (IPR)%s", GREEN, provider, RESET)
    session_messages = st.session_state.get("messages") or []
    lc_messages = _session_messages_to_lc(session_messages)
    initial_state: IPRState = {"messages": lc_messages}

    workflow = st.session_state.get("workflow")
    config = {"configurable": {"workflow": workflow}} if workflow else None

    graph = build_ipr_graph(provider=provider)
    result = graph.invoke(initial_state, config=config)

    result_messages = result.get("messages") or []
    num_initial = len(lc_messages)
    activity = _tool_activity_from_messages(result_messages, num_initial)

    final_content = None
    for m in reversed(result_messages):
        if isinstance(m, AIMessage) and (m.content or "").strip():
            final_content = m.content
            break

    if final_content is not None:
        msg = {"role": "AI", "content": final_content}
        if activity:
            msg["activity"] = activity
        st.session_state.messages.append(msg)
