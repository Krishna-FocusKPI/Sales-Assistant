"""
Right-side panel: workflow progress (bar + step count), flowchart, then end-workflow at the bottom.
Shared by PPR, MPR, and IPR; each workflow supplies its own steps and current-index logic.
"""
import streamlit as st

from .workflow_flow_steps import get_current_step_index, get_flow_steps


def _render_flowchart_blocks(steps: list[str], current_index: int) -> None:
    """Render flowchart as compact vertical step blocks."""
    steps_html = []
    for i, label in enumerate(steps):
        is_current = i == current_index
        bg = "rgba(100, 149, 237, 0.22)" if is_current else "rgba(0,0,0,0.05)"
        border = "2px solid #4169e1" if is_current else "1px solid #ccc"
        steps_html.append(
            f'<div style="width: 100%; padding: 0.2rem 0.45rem; margin: 0.08rem 0; border-radius: 4px; '
            f'background: {bg}; border: {border}; font-size: 0.8rem; color: #111111; font-weight: 500; '
            f'box-sizing: border-box; word-wrap: break-word; overflow-wrap: anywhere;">'
            f'{"→ " if is_current else "○ "}{label}'
            f'</div>'
        )
    block = (
        '<div style="padding: 0.1rem 0; max-width: 100%; box-sizing: border-box; overflow-x: hidden;">'
        + "".join(steps_html)
        + "</div>"
    )
    st.markdown(block, unsafe_allow_html=True)


def _render_workflow_panel(steps: list[str], current_index: int) -> None:
    """Render progress bar, flowchart, then end-workflow button at the bottom."""
    total = len(steps)

    st.markdown("#### Workflow progress")
    # Last step (e.g. 6/6): show a full bar. Earlier steps use +0.5 so the bar sits between step boundaries.
    if total and current_index >= total - 1:
        progress = 1.0
    else:
        progress = (current_index + 0.5) / total if total else 0
    st.progress(min(progress, 1.0), text=f"Step {current_index + 1} of {total}")

    st.markdown(
        '<hr style="margin: 0.4rem 0 0.35rem 0; border-color: #cccccc;">',
        unsafe_allow_html=True,
    )
    st.markdown("**Flowchart**")
    _render_flowchart_blocks(steps, current_index)

    with st.container(key="right_sidebar_end_actions"):
        if st.button("End current workflow", type="primary", key="right_panel_end_workflow"):
            st.session_state.show_end_workflow_confirm = True
            st.rerun()


def render_right_sidebar() -> None:
    """
    Render the right column: workflow progress, flowchart, end workflow (below chart).
    Dispatches by workflow name; PPR, MPR, and IPR each have defined steps and current-index logic.
    """
    workflow = st.session_state.get("workflow") or {}
    name = workflow.get("name")

    steps = get_flow_steps(name) if name else []
    if not steps:
        st.caption("No workflow progress for this flow.")
        return

    current_index = get_current_step_index(workflow)
    current_index = max(0, min(current_index, len(steps) - 1))
    _render_workflow_panel(steps, current_index)
