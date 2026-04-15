import streamlit as st
import pandas as pd


def _has_product_data():
    """True if workflow_memory has recommendations or filtered products to show."""
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
    """True if workflow_memory has a non-empty shopping list (selected products)."""
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


def _clear_products_modal_flag():
    if "show_products_modal" in st.session_state:
        st.session_state.show_products_modal = False


def _clear_selected_products_modal_flag():
    if "show_selected_products_modal" in st.session_state:
        st.session_state.show_selected_products_modal = False


def _clear_params_modal_flag():
    if "show_params_modal" in st.session_state:
        st.session_state.show_params_modal = False


def _clear_prompt_modal_flag():
    if "show_prompt_modal" in st.session_state:
        st.session_state.show_prompt_modal = False


def _clear_end_workflow_confirm_flag():
    if "show_end_workflow_confirm" in st.session_state:
        st.session_state.show_end_workflow_confirm = False


def _escape_markdown_cell(s: str) -> str:
    """Escape pipe and backslash so markdown table renders correctly."""
    if not isinstance(s, str):
        return str(s)
    return s.replace("\\", "\\\\").replace("|", "\\|")


@st.dialog("Selected product list", width="large", dismissible=True, on_dismiss=_clear_selected_products_modal_flag)
def show_selected_products_modal():
    """Modal showing the current shopping list (selected products). Same data as sidebar."""
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
        # Markdown table so item names are clickable links (like sidebar)
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


@st.dialog("Product recommendations", width="large", dismissible=True, on_dismiss=_clear_products_modal_flag)
def show_products_modal():
    """Modal showing current recommendations / filtered products (same data as Recommendation List tab)."""
    workflow = st.session_state.get("workflow")
    if not workflow:
        st.write("No workflow data.")
        return
    memory = workflow["workflow_memory"]
    filtered_products = getattr(memory, "filtered_products", None)
    all_available_products = getattr(memory, "all_available_products", None)
    filters = getattr(memory, "filters", None) or {}

    if (filtered_products is None or filtered_products.empty) and (
        all_available_products is None or all_available_products.empty
    ):
        st.write("No recommendations available yet.")
        return

    if filters and filtered_products is not None and not filtered_products.empty:
        st.write("**Recommended products matching your current criteria**")
        for k, v in filters.items():
            st.write(f"* **{k}:** {v}")
        st.dataframe(filtered_products, use_container_width=True)
        st.divider()

    st.write("**Full list of all products**")
    st.caption(f"Distributor: {getattr(memory, 'distributor_name', '—')} | Logo: {getattr(memory, 'logo_name', '—')} | Category: {getattr(memory, 'category', '—')}")
    if all_available_products is not None and not all_available_products.empty:
        st.dataframe(all_available_products, use_container_width=True)
    else:
        st.write("No full list available.")


PPR_PROMPT_SUGGESTIONS = """Try asking:
- *Validate a distributor* (e.g. "Distributor 246662" or your distributor ID)
- *Validate logo* (e.g. provide the company or logo name)
- *Product recommendations* (e.g. recommend a category or get products once distributor and logo are set)
- *Customize list* (filter, add or remove products)
- *Logo sales analysis* (e.g. "Run logo sales analysis" — required before building the deck)
- *Build deck* (create the sales deck when ready)

**Sample values (smoke test)** — use with bundled workflow pickles / `secrets.example.toml` categories:
| Step | Example you can paste |
| --- | --- |
| Distributor ID | `246662` |
| Logo (company) | `KOHLER CO.` |
| Category (after logo) | `Drinkware`, `Bags`, `Technology`, `Apparel`, `Stationery`, or `home & outdoor` |
| Later | `Add top 5`, `Run logo sales analysis`, then `Build the deck` |
"""


@st.dialog("Parameters collected", width="large", dismissible=True, on_dismiss=_clear_params_modal_flag)
def show_params_modal():
    """Modal showing parameters collected during the conversation."""
    workflow = st.session_state.get("workflow")
    if not workflow:
        st.write("No workflow data.")
        return
    memory = workflow["workflow_memory"]
    def _to_display(v):
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return None
        if hasattr(v, "item"):
            return v.item()
        return v
    params = [
        ("Distributor", _to_display(getattr(memory, "distributor_name", None))),
        ("Logo", _to_display(getattr(memory, "logo_name", None))),
        ("Have Recurring Revenue", _to_display(getattr(memory, "has_recurring", None))),
        ("Category", _to_display(getattr(memory, "category", None))),
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
    """Modal with suggested prompts for the workflow."""
    st.write("#### Prompt Suggestions")
    st.markdown(PPR_PROMPT_SUGGESTIONS)


@st.dialog("End workflow?", width="small", dismissible=True, on_dismiss=_clear_end_workflow_confirm_flag)
def show_end_workflow_confirm_modal():
    """Confirmation modal before ending the workflow."""
    st.warning("Ending the workflow will reset the chat and clear your current session. Are you sure you want to continue?")
    from .sidebar import clear_workflow
    with st.container(key="end_wf_modal_actions"):
        col_cancel, col_spacer, col_end = st.columns([1, 2, 1])
        with col_cancel:
            if st.button("Cancel", key="end_wf_cancel"):
                _clear_end_workflow_confirm_flag()
                st.rerun()
        with col_end:
            if st.button("End workflow", type="primary", key="end_wf_confirm"):
                _clear_end_workflow_confirm_flag()
                clear_workflow()


def _recommendation_tab():
    memory = st.session_state.workflow["workflow_memory"]
    filtered_products = getattr(memory, "filtered_products", None)
    all_available_products = getattr(memory, "all_available_products", None)
    filters = getattr(memory, "filters", None) or {}

    if (filtered_products is None or (hasattr(filtered_products, "empty") and filtered_products.empty)) and (
        all_available_products is None or (hasattr(all_available_products, "empty") and all_available_products.empty)
    ):
        st.write("No recommendations available, please check back later")
        return

    if filters and filtered_products is not None and not (hasattr(filtered_products, "empty") and filtered_products.empty):
        st.write("#### Recommended Products Matching Your Current Criteria")
        filter_string = "\n".join([f"* {k}: {v}" for k, v in filters.items()])
        st.write(filter_string)
        with st.expander("See the complete list of products"):
            st.dataframe(filtered_products)
        st.divider()

    st.write("#### Full List of All Products:")
    st.write(f"* Distributor: {getattr(memory, 'distributor_name', '—')}")
    st.write(f"* Logo: {getattr(memory, 'logo_name', '—')}")
    st.write(f"* Category: {getattr(memory, 'category', '—')}")
    with st.expander("See the complete list of products"):
        st.dataframe(all_available_products)

def _prompt_tab():
    """Same copy as the sidebar Prompt suggestions modal."""
    st.markdown(PPR_PROMPT_SUGGESTIONS)


def page_support():
    workflow_name = st.session_state.workflow.get("name", "PPR")
    st.title(f"💼 **{workflow_name}**")
    
    # set tabs
    prompt_tab, recommendation_tab = st.tabs([
        "Prompt Suggestion",
        "Recommendation List"
    ])
    
    
    with prompt_tab:
        _prompt_tab()


    with recommendation_tab:
        _recommendation_tab()