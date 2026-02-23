"""
IPR workflow bootstrap. Sets session state for the LangGraph path (no legacy graph).
"""
import streamlit as st

from .. import WorkFlows
from .memory import ToNextMemory, WorkFlowMemory
from .ui.ui import workflow_ui


def init_ipr_workflow():
    st.session_state.workflow["name"] = WorkFlows.WORKFLOW_IPR.value
    st.session_state.workflow["to_next_memory"] = ToNextMemory()
    st.session_state.workflow["workflow_memory"] = WorkFlowMemory()
    st.session_state.workflow["sidebar_params"] = {}
    st.session_state.workflow["ui"] = workflow_ui
