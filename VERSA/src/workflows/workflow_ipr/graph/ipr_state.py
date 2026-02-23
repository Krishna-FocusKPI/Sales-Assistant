"""
IPR LangGraph state: messages only. Workflow context lives in session (workflow_memory);
the agent gets context from the message history (tool results, etc.).
"""
from typing import Annotated, Sequence, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class IPRState(TypedDict, total=False):
    """State for the IPR graph: messages only."""

    messages: Annotated[Sequence[BaseMessage], add_messages]
