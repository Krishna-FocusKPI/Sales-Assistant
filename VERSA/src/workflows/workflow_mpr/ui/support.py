import pandas as pd
import streamlit as st


def _clear_params_modal_flag():
    if "show_params_modal" in st.session_state:
        st.session_state.show_params_modal = False


def _clear_prompt_modal_flag():
    if "show_prompt_modal" in st.session_state:
        st.session_state.show_prompt_modal = False


def _clear_products_modal_flag():
    if "show_products_modal" in st.session_state:
        st.session_state.show_products_modal = False


def _clear_end_workflow_confirm_flag():
    if "show_end_workflow_confirm" in st.session_state:
        st.session_state.show_end_workflow_confirm = False


def _has_product_data():
    if not st.session_state.get("workflow"):
        return False
    try:
        memory = st.session_state.workflow["workflow_memory"]
        fp = getattr(memory, "filtered_products", None)
        ap = getattr(memory, "all_available_products", None)
        if fp is not None and not (hasattr(fp, "empty") and fp.empty):
            return True
        if ap is not None and not (hasattr(ap, "empty") and ap.empty):
            return True
    except (KeyError, TypeError):
        pass
    return False


MPR_PROMPT_SUGGESTIONS = """Try asking:
- *Validate a distributor* (e.g. "Distributor 246662" or your distributor ID)
- *Validate a category* (e.g. "Bags" or your product category)
- *Get recommendations* (e.g. "Give me product recommendations" once distributor and category are set)

**Sample values (smoke test)** — distributor + category from `secrets.example.toml` `[mpr.categories]`:
| Step | Example you can paste |
| --- | --- |
| Distributor ID | `246662` |
| Category | `Drinkware`, `Bags`, `Technology`, `Apparel`, `Stationery`, or `home & outdoor` |
| Then | `Give me product recommendations` |
"""


def render_mpr_params_panel() -> None:
    workflow = st.session_state.get("workflow")
    if not workflow:
        st.write("No workflow data.")
        return
    memory = workflow["workflow_memory"]
    params = [
        ("Distributor", getattr(memory, "distributor_name", None) or getattr(memory, "distributor_id", None)),
        ("Category", getattr(memory, "category", None)),
    ]
    params_df = pd.DataFrame(params, columns=["Parameter", "Value"])
    params_df.dropna(inplace=True)
    if params_df.empty:
        st.write("No parameters collected yet.")
        return
    params_df = params_df.astype(str)
    st.dataframe(params_df, use_container_width=True, hide_index=True)


def render_mpr_prompts_panel() -> None:
    st.write("#### Prompt suggestions")
    st.markdown(MPR_PROMPT_SUGGESTIONS)


def render_mpr_products_panel() -> None:
    workflow = st.session_state.get("workflow")
    if not workflow:
        st.write("No workflow data.")
        return
    memory = workflow["workflow_memory"]
    filtered_products = getattr(memory, "filtered_products", None)
    all_available_products = getattr(memory, "all_available_products", None)
    filters = getattr(memory, "filters", None) or {}
    if (filtered_products is None or (hasattr(filtered_products, "empty") and filtered_products.empty)) and (
        all_available_products is None or (hasattr(all_available_products, "empty") and all_available_products.empty)
    ):
        st.write("No recommendations available yet.")
        return
    if filters and filtered_products is not None and not (hasattr(filtered_products, "empty") and filtered_products.empty):
        st.write("**Recommended products matching your current criteria**")
        for k, v in filters.items():
            st.write(f"* **{k}:** {v}")
        st.dataframe(filtered_products, use_container_width=True)
        st.divider()
    st.write("**Full list of all products**")
    distributor = getattr(memory, "distributor_name", None) or getattr(memory, "distributor_id", None)
    if distributor:
        st.caption(f"Distributor: {distributor}")
    if getattr(memory, "category", None):
        st.caption(f"Category: {memory.category}")
    if all_available_products is not None and not (hasattr(all_available_products, "empty") and all_available_products.empty):
        st.dataframe(all_available_products, use_container_width=True)
    else:
        st.write("No full list available.")


@st.dialog("Parameters collected", width="large", dismissible=True, on_dismiss=_clear_params_modal_flag)
def show_params_modal():
    render_mpr_params_panel()


@st.dialog("Prompt suggestions", width="large", dismissible=True, on_dismiss=_clear_prompt_modal_flag)
def show_prompt_modal():
    render_mpr_prompts_panel()


@st.dialog("Product recommendations", width="large", dismissible=True, on_dismiss=_clear_products_modal_flag)
def show_products_modal():
    render_mpr_products_panel()


@st.dialog("End workflow?", width="small", dismissible=True, on_dismiss=_clear_end_workflow_confirm_flag)
def show_end_workflow_confirm_modal():
    st.warning("Ending the workflow will reset the chat and clear your current session. Are you sure you want to continue?")
    from .sidebar import clear_workflow
    with st.container(key="end_wf_modal_actions"):
        col_cancel, col_spacer, col_end = st.columns([1, 2, 1])
        with col_cancel:
            if st.button("Cancel", key="mpr_end_wf_cancel"):
                _clear_end_workflow_confirm_flag()
                st.rerun()
        with col_end:
            if st.button("End workflow", type="primary", key="mpr_end_wf_confirm"):
                _clear_end_workflow_confirm_flag()
                clear_workflow()
