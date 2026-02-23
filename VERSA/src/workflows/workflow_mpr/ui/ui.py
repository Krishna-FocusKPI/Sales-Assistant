import streamlit as st

from .support import (
    show_end_workflow_confirm_modal,
    show_params_modal,
    show_prompt_modal,
    show_products_modal,
)
from .sidebar import page_sidebar


def workflow_ui(page_chatting):
    st.sidebar.title(st.session_state.workflow["name"])
    page_sidebar()
    page_chatting()
    if st.session_state.get("show_products_modal"):
        show_products_modal()
    if st.session_state.get("show_params_modal"):
        show_params_modal()
    if st.session_state.get("show_prompt_modal"):
        show_prompt_modal()
    if st.session_state.get("show_end_workflow_confirm"):
        show_end_workflow_confirm_modal()
