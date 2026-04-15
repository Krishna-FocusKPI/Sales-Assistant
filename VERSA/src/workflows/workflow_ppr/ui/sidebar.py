import streamlit as st

from src.common.deck_download_ui import render_deck_download_if_ready

from .support import _has_product_data, _has_selected_products


def clear_workflow():
    """Reset workflow and chat to initial state (like first load)."""
    st.session_state.workflow = {}
    st.session_state.messages = [
        {"role": "AI", "content": st.secrets.message.intro}
    ]
    st.rerun()


def page_sidebar():
    """Sidebar: links that open modals (recommended products, selected products, params, prompt suggestions). End workflow opens confirmation modal."""
    st.sidebar.caption("Open in modal")
    if _has_product_data():
        if st.sidebar.button("Recommended products", key="sidebar_view_products"):
            st.session_state.show_products_modal = True
            st.rerun()
    if _has_selected_products():
        if st.sidebar.button("Selected products", key="sidebar_view_selected"):
            st.session_state.show_selected_products_modal = True
            st.rerun()
    if st.sidebar.button("Parameters collected", key="sidebar_params"):
        st.session_state.show_params_modal = True
        st.rerun()
    if st.sidebar.button("Prompt suggestions", key="sidebar_prompt"):
        st.session_state.show_prompt_modal = True
        st.rerun()

    render_deck_download_if_ready(key_prefix="versa_deck")

    st.sidebar.divider()
    if st.sidebar.button("End current workflow", type="primary", key="sidebar_end_workflow"):
        st.session_state.show_end_workflow_confirm = True
        st.rerun()
