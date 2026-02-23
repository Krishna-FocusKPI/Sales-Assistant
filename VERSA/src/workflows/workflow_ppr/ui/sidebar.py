import streamlit as st

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

    st.sidebar.divider()
    if st.sidebar.button("End current workflow", type="primary", key="sidebar_end_workflow"):
        st.session_state.show_end_workflow_confirm = True
        st.rerun()
