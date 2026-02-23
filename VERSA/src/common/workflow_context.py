"""
Thread-local workflow context for PPR tools.
When the LangGraph ToolNode runs tools in a worker thread, st.session_state is not
available. We pass workflow via graph config and set it here so tools can read it.
"""
import threading

_workflow_context: threading.local = threading.local()


def set_workflow(workflow: dict) -> None:
    """Set the workflow dict for the current thread (used by PPR tool node)."""
    _workflow_context.workflow = workflow


def clear_workflow() -> None:
    """Clear the workflow for the current thread."""
    if hasattr(_workflow_context, "workflow"):
        del _workflow_context.workflow


def get_workflow():
    """
    Return the workflow dict for the current context.
    Prefer thread-local (set when running inside LangGraph tool node), else streamlit session.
    Use this in PPR tools so they work both in the main thread (legacy) and in worker threads (LangGraph).
    """
    try:
        w = getattr(_workflow_context, "workflow", None)
        if w is not None:
            return w
    except Exception:
        pass
    try:
        import streamlit as st
        return st.session_state.get("workflow")
    except Exception:
        return None
