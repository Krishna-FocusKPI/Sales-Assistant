"""
General chat (CBT) LangGraph state: messages only. No tools.
"""
from typing import Annotated, Sequence, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class ChatState(TypedDict, total=False):
    """State for the general chat graph: messages only."""

    messages: Annotated[Sequence[BaseMessage], add_messages]
