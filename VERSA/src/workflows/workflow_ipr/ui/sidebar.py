import streamlit as st

from .support import (
    render_ipr_naics_panel,
    render_ipr_params_panel,
    render_ipr_products_panel,
    render_ipr_prompts_panel,
    render_ipr_selected_products_panel,
)


def clear_workflow():
    st.session_state.workflow = {}
    st.session_state.messages = [
        {"role": "AI", "content": st.secrets.message.intro}
    ]
    st.rerun()


def page_sidebar():
    st.sidebar.caption("Workflow data (tabs)")
    tab_products, tab_selected, tab_params, tab_prompts, tab_naics = st.sidebar.tabs(
        ["Products", "Selected", "Parameters", "Prompts", "NAICS"]
    )
    with tab_products:
        render_ipr_products_panel()
    with tab_selected:
        render_ipr_selected_products_panel()
    with tab_params:
        render_ipr_params_panel()
    with tab_prompts:
        render_ipr_prompts_panel()
    with tab_naics:
        render_ipr_naics_panel()
