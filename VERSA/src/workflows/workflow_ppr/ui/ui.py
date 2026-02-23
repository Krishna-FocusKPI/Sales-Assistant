import streamlit as st

from .support import (
    show_end_workflow_confirm_modal,
    show_params_modal,
    show_prompt_modal,
    show_products_modal,
    show_selected_products_modal,
)
from .sidebar import page_sidebar


def workflow_ui(page_chatting):
    """Always show chat as main content. Sidebar has links that open modals."""
    st.sidebar.title(st.session_state.workflow["name"])
    page_sidebar()
    # Main content is always chat
    page_chatting()
    # Open modals when requested (from sidebar or from chat-area buttons)
    if st.session_state.get("show_products_modal"):
        show_products_modal()
    if st.session_state.get("show_selected_products_modal"):
        show_selected_products_modal()
    if st.session_state.get("show_params_modal"):
        show_params_modal()
    if st.session_state.get("show_prompt_modal"):
        show_prompt_modal()
    if st.session_state.get("show_end_workflow_confirm"):
        show_end_workflow_confirm_modal()
