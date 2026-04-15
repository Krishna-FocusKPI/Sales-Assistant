"""
Wire MPR LangGraph to Streamlit. Same pattern as PPR.
"""
import logging

import streamlit as st
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage

from src.common.chat_products_embed import build_products_chat_embed_from_memory

from .mpr_graph import build_mpr_graph
from .mpr_state import MPRState

GREEN = "\033[32m"
RESET = "\033[0m"


def _tool_activity_from_messages(messages: list, start_index: int) -> list[str]:
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
    out = []
    for m in session_messages:
        role = (m.get("role") or "").strip().lower()
        content = m.get("content") or ""
        if role == "human":
            out.append(HumanMessage(content=content))
        else:
            out.append(AIMessage(content=content))
    return out


def run_mpr_turn(user_message: str, *, provider: str = "openai") -> None:
    logging.info("%sUsing provider: %s (MPR)%s", GREEN, provider, RESET)
    session_messages = st.session_state.get("messages") or []
    lc_messages = _session_messages_to_lc(session_messages)
    initial_state: MPRState = {"messages": lc_messages}

    workflow = st.session_state.get("workflow")
    config = {"configurable": {"workflow": workflow}} if workflow else None

    graph = build_mpr_graph(provider=provider)
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
        content = final_content if isinstance(final_content, str) else str(final_content)
        products_chat_embed = None
        if activity and "product_recommendation" in activity:
            wf = st.session_state.get("workflow") or {}
            mem = wf.get("workflow_memory")
            if mem is not None:
                products_chat_embed = build_products_chat_embed_from_memory(mem, variant="mpr")
        msg = {"role": "AI", "content": content}
        if products_chat_embed:
            msg["products_chat_embed"] = products_chat_embed
        if activity:
            msg["activity"] = activity
        st.session_state.messages.append(msg)
