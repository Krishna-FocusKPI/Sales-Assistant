"""
Wire general chat (CBT) LangGraph to Streamlit. No tools; appends AI reply to session messages.
"""
import logging

import streamlit as st
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from .cbt_graph import build_cbt_graph
from .cbt_state import ChatState


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


def run_chatbot_turn(user_message: str, *, provider: str = "openai") -> None:
    """
    Run one general-chat LangGraph turn. Session messages already include the latest
    human message; we invoke the graph and append the AI response.
    """
    logging.info("General chat turn (provider: %s)", provider)
    session_messages = st.session_state.get("messages") or []
    lc_messages = _session_messages_to_lc(session_messages)
    initial_state: ChatState = {"messages": lc_messages}

    graph = build_cbt_graph(provider=provider)
    result = graph.invoke(initial_state)

    result_messages = result.get("messages") or []
    final_content = None
    for m in reversed(result_messages):
        if isinstance(m, AIMessage) and (m.content or "").strip():
            final_content = m.content
            break

    if final_content is not None:
        st.session_state.messages.append({"role": "AI", "content": final_content})
