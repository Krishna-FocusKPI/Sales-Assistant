"""Streamlit download for PPR/IPR decks saved on the server (sidebar and/or chat)."""

from __future__ import annotations

import hashlib
from typing import Any, Optional

import streamlit as st

from src.utils.versa_paths import resolve_saved_deck_path
from src.workflows import WorkFlows


def _deck_signature_for_memory(workflow_memory: Any) -> Optional[str]:
    """Stable id for the current on-disk deck file (path + mtime), or None if no file."""
    if workflow_memory is None:
        return None
    path = resolve_saved_deck_path(workflow_memory)
    if path is None:
        return None
    try:
        resolved = path.resolve()
        return f"{resolved}:{path.stat().st_mtime_ns}"
    except OSError:
        return str(path)


def dismiss_chat_deck_offer_if_deck_ready() -> None:
    """Call when the user sends a new chat message so the one-time chat download control hides."""
    wf = st.session_state.get("workflow")
    if not wf:
        return
    mem = wf.get("workflow_memory")
    sig = _deck_signature_for_memory(mem)
    if sig:
        st.session_state["versa_chat_deck_dismissed_sig"] = sig


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


def render_chat_deck_download_if_ready() -> None:
    """
    One-time download in the main chat column (below messages, above input).
    Hidden after the user downloads, or after they send their next message, for this deck file.
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
    sig = _deck_signature_for_memory(mem)
    if sig is None:
        return
    if st.session_state.get("versa_chat_deck_dismissed_sig") == sig:
        return

    with open(path, "rb") as fp:
        data = fp.read()

    key_hash = hashlib.sha256(sig.encode("utf-8")).hexdigest()[:24]

    def _on_download_click() -> None:
        st.session_state["versa_chat_deck_dismissed_sig"] = sig

    st.caption("Deck ready")
    st.download_button(
        "Download PowerPoint deck",
        data=data,
        file_name=path.name,
        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        key=f"versa_chat_deck_{key_hash}",
        type="secondary",
        use_container_width=True,
        on_click=_on_download_click,
    )
