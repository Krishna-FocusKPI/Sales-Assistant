import streamlit as st

from .support import (
    render_ppr_params_panel,
    render_ppr_products_panel,
    render_ppr_prompts_panel,
    render_ppr_selected_products_panel,
)


def clear_workflow():
    """Reset workflow and chat to initial state (like first load)."""
    st.session_state.workflow = {}
    st.session_state.messages = [
        {"role": "AI", "content": st.secrets.message.intro}
    ]
    st.rerun()


def page_sidebar():
    """Sidebar: tabbed panels for products, selected list, parameters, and prompts. End workflow is in the right column."""
    st.sidebar.caption("Workflow data (tabs)")
    tab_products, tab_selected, tab_params, tab_prompts = st.sidebar.tabs(
        ["Products", "Selected", "Parameters", "Prompts"]
    )
    with tab_products:
        render_ppr_products_panel()
    with tab_selected:
        render_ppr_selected_products_panel()
    with tab_params:
        render_ppr_params_panel()
    with tab_prompts:
        render_ppr_prompts_panel()
