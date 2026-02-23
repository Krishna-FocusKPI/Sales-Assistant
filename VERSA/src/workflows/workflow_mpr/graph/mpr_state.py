"""
MPR LangGraph state: messages only. Workflow context in session (workflow_memory).
"""
from typing import Annotated, Sequence, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class MPRState(TypedDict, total=False):
    """State for the MPR graph: messages only."""

    messages: Annotated[Sequence[BaseMessage], add_messages]
