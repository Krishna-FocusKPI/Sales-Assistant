"""Streamlit sidebar download for PPR/IPR decks saved on the server."""

from __future__ import annotations

import streamlit as st

from src.utils.versa_paths import resolve_saved_deck_path
from src.workflows import WorkFlows


def render_deck_download_if_ready(key_prefix: str = "versa_deck") -> None:
    """
    If the active workflow is PPR or IPR and a built .pptx exists, show a sidebar download button.
    """
    wf = st.session_state.get("workflow")
    if not wf:
        return
    name = wf.get("name")
    if name not in (WorkFlows.WORKFLOW_PPR.value, WorkFlows.WORKFLOW_IPR.value):
        return
    mem = wf.get("workflow_memory")
    path = resolve_saved_deck_path(mem)
    if path is None:
        return

    st.sidebar.caption("Deck file")
    with open(path, "rb") as fp:
        data = fp.read()
    st.sidebar.download_button(
        "Download PowerPoint deck",
        data=data,
        file_name=path.name,
        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        key=f"{key_prefix}_sidebar_{name.replace(' ', '_')}",
    )
