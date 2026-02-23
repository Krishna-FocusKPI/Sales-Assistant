import pandas as pd
import streamlit as st

from src.utils.initialization import cache_naics_code


def _clear_params_modal_flag():
    if "show_params_modal" in st.session_state:
        st.session_state.show_params_modal = False


def _clear_prompt_modal_flag():
    if "show_prompt_modal" in st.session_state:
        st.session_state.show_prompt_modal = False


def _clear_products_modal_flag():
    if "show_products_modal" in st.session_state:
        st.session_state.show_products_modal = False


def _clear_selected_products_modal_flag():
    if "show_selected_products_modal" in st.session_state:
        st.session_state.show_selected_products_modal = False


def _clear_naics_modal_flag():
    if "show_naics_modal" in st.session_state:
        st.session_state.show_naics_modal = False


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


def _has_selected_products():
    if not st.session_state.get("workflow"):
        return False
    try:
        memory = st.session_state.workflow["workflow_memory"]
        sl = getattr(memory, "shopping_list", None)
        if sl is not None and hasattr(sl, "empty") and not sl.empty:
            return True
    except (KeyError, TypeError):
        pass
    return False


def _escape_markdown_cell(s: str) -> str:
    if not isinstance(s, str):
        return str(s)
    return s.replace("\\", "\\\\").replace("|", "\\|")


IPR_PROMPT_SUGGESTIONS = """Try these in the chat to move the IPR workflow along:

- **Validate NAICS:** e.g. `23` or `541512`
- **Pick a category:** e.g. `Drinkware`, `Bags`, `Technology`
- **Get recommendations:** e.g. "Get product recommendations"
- **Filter:** e.g. "Show me items under $20" or "blue tumblers"
- **Add products:** e.g. "Add top 3" or "Add product 1234-56"
- **Remove:** e.g. "Remove product 1234-56"
- **Build deck:** e.g. "Build the deck" when you're ready"""


@st.dialog("Parameters collected", width="large", dismissible=True, on_dismiss=_clear_params_modal_flag)
def show_params_modal():
    workflow = st.session_state.get("workflow")
    if not workflow:
        st.write("No workflow data.")
        return
    memory = workflow["workflow_memory"]
    params = [
        ("NAICS Code", getattr(memory, "naics_code", None)),
        ("Industry", getattr(memory, "industry", None)),
        ("Category", getattr(memory, "category", None)),
    ]
    params_df = pd.DataFrame(params, columns=["Parameter", "Value"])
    params_df.dropna(inplace=True)
    if params_df.empty:
        st.write("No parameters collected yet.")
        return
    params_df = params_df.astype(str)
    st.dataframe(params_df, use_container_width=True, hide_index=True)


@st.dialog("Prompt suggestions", width="large", dismissible=True, on_dismiss=_clear_prompt_modal_flag)
def show_prompt_modal():
    st.write("#### Prompt Suggestions")
    st.markdown(IPR_PROMPT_SUGGESTIONS)


@st.dialog("NAICS code list", width="large", dismissible=True, on_dismiss=_clear_naics_modal_flag)
def show_naics_modal():
    st.write("#### Full list of NAICS codes")
    df = cache_naics_code()
    st.dataframe(df, use_container_width=True, hide_index=True)


@st.dialog("Product recommendations", width="large", dismissible=True, on_dismiss=_clear_products_modal_flag)
def show_products_modal():
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
    st.caption(f"Industry: {getattr(memory, 'industry', '—')} | Category: {getattr(memory, 'category', '—')}")
    if all_available_products is not None and not (hasattr(all_available_products, "empty") and all_available_products.empty):
        st.dataframe(all_available_products, use_container_width=True)
    else:
        st.write("No full list available.")


@st.dialog("Selected product list", width="large", dismissible=True, on_dismiss=_clear_selected_products_modal_flag)
def show_selected_products_modal():
    workflow = st.session_state.get("workflow")
    if not workflow:
        st.write("No workflow data.")
        return
    memory = workflow["workflow_memory"]
    shopping_list = getattr(memory, "shopping_list", None)
    if shopping_list is None or (hasattr(shopping_list, "empty") and shopping_list.empty):
        st.write("No products selected yet.")
        return
    st.write("**Selected product list**")
    has_url = "URL" in shopping_list.columns and "ITEM_NAME" in shopping_list.columns
    if has_url:
        rows = ["| Item ID | Item name |", "| --- | --- |"]
        for _, row in shopping_list.iterrows():
            item_id = _escape_markdown_cell(str(row.get("ITEM_ID", "")))
            name = str(row.get("ITEM_NAME", ""))
            url = str(row.get("URL", ""))
            link = f"[{_escape_markdown_cell(name)}]({url})" if url else _escape_markdown_cell(name)
            rows.append(f"| {item_id} | {link} |")
        st.markdown("\n".join(rows))
    else:
        df = shopping_list[["ITEM_ID", "ITEM_NAME"]].copy() if "ITEM_NAME" in shopping_list.columns else shopping_list
        st.dataframe(df, use_container_width=True)


@st.dialog("End workflow?", width="small", dismissible=True, on_dismiss=_clear_end_workflow_confirm_flag)
def show_end_workflow_confirm_modal():
    st.warning("Ending the workflow will reset the chat and clear your current session. Are you sure you want to continue?")
    from .sidebar import clear_workflow
    with st.container(key="end_wf_modal_actions"):
        col_spacer, col_cancel, col_end = st.columns([2, 1, 1])
        with col_cancel:
            if st.button("Cancel", key="ipr_end_wf_cancel"):
                _clear_end_workflow_confirm_flag()
                st.rerun()
        with col_end:
            if st.button("End workflow", type="primary", key="ipr_end_wf_confirm"):
                _clear_end_workflow_confirm_flag()
                clear_workflow()
