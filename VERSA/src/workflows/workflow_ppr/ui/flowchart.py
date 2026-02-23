"""
PPR workflow flowchart: show steps and highlight current from workflow_memory.
Uses common workflow_flow_steps for step list and current-index logic.
"""
import streamlit as st

from src.common.workflow_flow_steps import PPR_FLOW_STEPS, get_current_step_index


def _current_step_index():
    """Infer current step 0..len(PPR_FLOW_STEPS) from workflow_memory (for PPR only)."""
    w = st.session_state.get("workflow") or {}
    return get_current_step_index(w)


def render_ppr_flowchart():
    """Render the PPR flowchart: boxes for each step, current step highlighted."""
    _render_ppr_flowchart_html(compact=False, in_sidebar=False)


def render_ppr_flowchart_sidebar():
    """Render a compact PPR flowchart in the sidebar (fixed container, unaffected by chat scroll)."""
    _render_ppr_flowchart_html(compact=True, in_sidebar=True)


def _render_ppr_flowchart_html(*, compact: bool, in_sidebar: bool = False):
    current = _current_step_index()
    steps_html = []
    pad = "0.25rem 0.4rem" if compact else "0.5rem 0.75rem"
    margin = "0.15rem 0" if compact else "0.25rem 0"
    fsize = "0.75rem" if compact else "0.9rem"
    for i, label in enumerate(PPR_FLOW_STEPS):
        is_current = i == current
        bg = "rgba(100, 149, 237, 0.25)" if is_current else "rgba(0,0,0,0.04)"
        border = "2px solid #6495ed" if is_current else "1px solid #ddd"
        steps_html.append(
            f'<div style="padding: {pad}; margin: {margin}; border-radius: 4px; '
            f'background: {bg}; border: {border}; font-size: {fsize};">'
            f'{"→ " if is_current else ""}{label}'
            f'</div>'
        )
    title_style = "font-weight: 600; font-size: 0.8rem; margin-bottom: 0.35rem;" if compact else "font-weight: 600; margin-bottom: 0.5rem;"
    caption_style = "font-size: 0.7rem; color: var(--text-muted, #666); margin-top: 0.35rem;" if compact else "font-size: 0.8rem; color: var(--text-muted, #666); margin-top: 0.5rem;"
    block = (
        '<div style="padding: 0.25rem 0;">'
        f'<p style="{title_style}">Workflow progress</p>'
        + "".join(steps_html) +
        f'<p style="{caption_style}">Current step highlighted</p>'
        '</div>'
    )
    (st.sidebar.markdown if in_sidebar else st.markdown)(block, unsafe_allow_html=True)
