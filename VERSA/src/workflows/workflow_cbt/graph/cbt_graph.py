"""
General chat LangGraph: single agent node, no tools.
Uses last N messages as context (same idea as ConversationBufferWindowMemory k=5).
"""
from typing import Literal

from langchain_core.messages import AIMessage, BaseMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from src.common.provider import get_chat_model

from .cbt_prompts import CBT_SYSTEM_PROMPT
from .cbt_state import ChatState

# Same effective context as legacy ConversationBufferWindowMemory(k=5): 5 exchange pairs = 10 messages
MAX_MESSAGES_CONTEXT = 10


def _agent_node(state: ChatState, *, provider: Literal["openai", "anthropic"] = "openai") -> dict:
    """Run the chat model on messages; return the new AI message."""
    messages = list(state.get("messages") or [])
    if not messages:
        return {"messages": []}
    # Last message should be from human (run_chatbot_turn passes session messages with human at end)
    context = messages[:-1] if len(messages) > 1 else []
    context = context[-MAX_MESSAGES_CONTEXT:] if len(context) > MAX_MESSAGES_CONTEXT else context
    system = SystemMessage(content=CBT_SYSTEM_PROMPT)
    model = get_chat_model(provider, temperature=0, max_tokens=2000)
    to_send = [system] + context + [messages[-1]]
    response = model.invoke(to_send)
    if isinstance(response, AIMessage):
        return {"messages": [response]}
    return {"messages": [AIMessage(content=response.content if hasattr(response, "content") else str(response))]}


def build_cbt_graph(provider: Literal["openai", "anthropic"] = "openai"):
    """Build and compile the general chat graph. One agent node, no tools."""
    graph = StateGraph(ChatState)
    graph.add_node("agent", lambda s: _agent_node(s, provider=provider))
    graph.add_edge(START, "agent")
    graph.add_edge("agent", END)
    return graph.compile()
