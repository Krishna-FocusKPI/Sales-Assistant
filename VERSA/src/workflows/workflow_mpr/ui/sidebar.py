import streamlit as st

from src.common.provider import SUPPORTED_PROVIDERS
from .support import render_mpr_params_panel, render_mpr_products_panel, render_mpr_prompts_panel

PROVIDER_LABELS = {"openai": "OpenAI", "anthropic": "Anthropic"}


def _mpr_sidebar_provider_to_header() -> None:
    """Keep chat header `ppr_provider` in sync when the MPR sidebar model changes."""
    st.session_state["ppr_provider"] = st.session_state.get("mpr_provider_sidebar", "openai")


def clear_workflow():
    st.session_state.workflow = {}
    st.session_state.messages = [
        {"role": "AI", "content": st.secrets.message.intro}
    ]
    st.rerun()


def page_sidebar():
    st.session_state.setdefault("mpr_provider_sidebar", st.session_state.get("ppr_provider", "openai"))
    st.sidebar.selectbox(
        "Model provider",
        options=list(SUPPORTED_PROVIDERS),
        format_func=lambda p: PROVIDER_LABELS.get(p, p.title()),
        key="mpr_provider_sidebar",
        on_change=_mpr_sidebar_provider_to_header,
    )
    st.sidebar.divider()
    st.sidebar.caption("Workflow data (tabs)")
    tab_products, tab_params, tab_prompts = st.sidebar.tabs(["Products", "Parameters", "Prompts"])
    with tab_products:
        render_mpr_products_panel()
    with tab_params:
        render_mpr_params_panel()
    with tab_prompts:
        render_mpr_prompts_panel()
