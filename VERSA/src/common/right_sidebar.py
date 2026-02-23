"""
Right-side panel: flowchart, progress meter, current step, next recommended step.
Shared by PPR, MPR, and IPR; each workflow supplies its own steps and current-index logic.
"""
import streamlit as st

from .workflow_flow_steps import (
    get_current_step_index,
    get_flow_steps,
    get_next_step_index,
)


def _render_flowchart_blocks(steps: list[str], current_index: int) -> None:
    """Render flowchart as compact vertical step blocks."""
    steps_html = []
    for i, label in enumerate(steps):
        is_current = i == current_index
        bg = "rgba(100, 149, 237, 0.3)" if is_current else "rgba(0,0,0,0.06)"
        border = "2px solid #6495ed" if is_current else "1px solid #ddd"
        steps_html.append(
            f'<div style="padding: 0.2rem 0.35rem; margin: 0.08rem 0; border-radius: 4px; '
            f'background: {bg}; border: {border}; font-size: 0.8rem; color: #fff; font-weight: 500;">'
            f'{"→ " if is_current else "○ "}{label}'
            f'</div>'
        )
    block = '<div style="padding: 0.1rem 0;">' + "".join(steps_html) + "</div>"
    st.markdown(block, unsafe_allow_html=True)


def _render_workflow_panel(workflow_name: str, steps: list[str], current_index: int) -> None:
    """Render progress, current step, next step, and flowchart for any workflow."""
    total = len(steps)
    current_step_name = steps[current_index] if 0 <= current_index < total else "—"
    next_i = get_next_step_index(workflow_name, current_index, total)
    next_step_name = steps[next_i] if next_i < total else "Complete"

    st.markdown("#### Workflow progress")
    progress = (current_index + 0.5) / total if total else 0
    st.progress(min(progress, 1.0), text=f"Step {current_index + 1} of {total}")

    st.markdown("**Current step**")
    st.info(current_step_name)

    st.markdown("**Next recommended step**")
    st.success(next_step_name)

    st.markdown(
        '<hr style="margin: 0.4rem 0 0.35rem 0; border-color: rgba(255,255,255,0.2);">',
        unsafe_allow_html=True,
    )
    st.markdown("**Flowchart**")
    _render_flowchart_blocks(steps, current_index)


def render_right_sidebar() -> None:
    """
    Render the right sidebar content (flowchart, progress, current step, next step).
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
    _render_workflow_panel(name, steps, current_index)
