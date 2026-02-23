import streamlit as st

from src.common.provider import SUPPORTED_PROVIDERS
from .support import _has_product_data

PROVIDER_LABELS = {"openai": "OpenAI", "anthropic": "Anthropic"}


def clear_workflow():
    st.session_state.workflow = {}
    st.session_state.messages = [
        {"role": "AI", "content": st.secrets.message.intro}
    ]
    st.rerun()


def page_sidebar():
    # Light background for modal-opener buttons so text is readable (avoid white-on-white)
    st.sidebar.markdown(
        """
        <style>
        [data-testid="stSidebar"] .stButton > button[kind="secondary"] {
            background-color: rgba(255, 255, 255, 0.12) !important;
            backdrop-filter: blur(8px);
            -webkit-backdrop-filter: blur(8px);
            color: #1f2937 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.session_state.setdefault("ppr_provider_sidebar", st.session_state.get("ppr_provider", "openai"))
    st.sidebar.selectbox(
        "Model provider",
        options=list(SUPPORTED_PROVIDERS),
        format_func=lambda p: PROVIDER_LABELS.get(p, p.title()),
        key="ppr_provider_sidebar",
    )
    st.sidebar.divider()
    st.sidebar.caption("Open in modal")
    if _has_product_data():
        if st.sidebar.button("Recommended products", key="mpr_sidebar_products"):
            st.session_state.show_products_modal = True
            st.rerun()
    if st.sidebar.button("Parameters collected", key="mpr_sidebar_params"):
        st.session_state.show_params_modal = True
        st.rerun()
    if st.sidebar.button("Prompt suggestions", key="mpr_sidebar_prompt"):
        st.session_state.show_prompt_modal = True
        st.rerun()
    st.sidebar.divider()
    if st.sidebar.button("End current workflow", type="primary", key="mpr_sidebar_end"):
        st.session_state.show_end_workflow_confirm = True
        st.rerun()
