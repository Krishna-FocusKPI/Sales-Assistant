"""Snapshot + render product recommendation tables inside chat (same layout as modal/sidebar)."""

from __future__ import annotations

from io import StringIO
from typing import Any

import pandas as pd
import streamlit as st

# Fixed height so the grid scrolls inside the assistant bubble (like a constrained modal body).
CHAT_PRODUCTS_TABLE_HEIGHT = 420


def _df_to_json_records(df: pd.DataFrame) -> str:
    return df.to_json(orient="records", date_format="iso", default_handler=str)


def _df_from_json_records(s: str) -> pd.DataFrame:
    return pd.read_json(StringIO(s), orient="records")


def build_products_chat_embed_from_memory(memory: Any, *, variant: str) -> dict[str, Any] | None:
    """
    Build a JSON-serializable payload so each chat row keeps its own table after workflow memory updates.
    Layout matches `render_*_products_panel` (filtered block + full list + captions).
    """
    filtered_products = getattr(memory, "filtered_products", None)
    all_available_products = getattr(memory, "all_available_products", None)
    filters = getattr(memory, "filters", None) or {}

    full_empty = all_available_products is None or (
        hasattr(all_available_products, "empty") and all_available_products.empty
    )
    if full_empty:
        return None

    embed: dict[str, Any] = {
        "variant": variant,
        "full_list_json": _df_to_json_records(all_available_products),
    }

    if filters and filtered_products is not None and not (
        hasattr(filtered_products, "empty") and filtered_products.empty
    ):
        embed["show_filtered"] = True
        embed["filters"] = {str(k): str(v) for k, v in filters.items()}
        embed["filtered_json"] = _df_to_json_records(filtered_products)
    else:
        embed["show_filtered"] = False

    if variant == "ppr":
        embed["caption"] = (
            f"Distributor: {getattr(memory, 'distributor_name', '—')} | Logo: {getattr(memory, 'logo_name', '—')} | "
            f"Category: {getattr(memory, 'category', '—')}"
        )
    elif variant == "mpr":
        distributor = getattr(memory, "distributor_name", None) or getattr(memory, "distributor_id", None)
        embed["mpr_distributor"] = distributor
        embed["mpr_category"] = getattr(memory, "category", None)
    elif variant == "ipr":
        embed["ipr_caption"] = (
            f"Industry: {getattr(memory, 'industry', '—')} | Category: {getattr(memory, 'category', '—')}"
        )
    return embed


def render_products_chat_embed(embed: dict[str, Any], *, key_suffix: str) -> None:
    """Render the same structure as the Product recommendations modal (scrollable dataframe)."""
    if embed.get("show_filtered") and embed.get("filtered_json"):
        st.write("**Recommended products matching your current criteria**")
        for k, v in (embed.get("filters") or {}).items():
            st.write(f"* **{k}:** {v}")
        st.dataframe(
            _df_from_json_records(embed["filtered_json"]),
            use_container_width=True,
            key=f"versa_chat_pf_{key_suffix}",
        )
        st.divider()

    st.write("**Full list of all products**")
    variant = embed.get("variant") or "ppr"
    if variant == "ppr":
        st.caption(embed.get("caption") or "")
    elif variant == "mpr":
        if embed.get("mpr_distributor"):
            st.caption(f"Distributor: {embed['mpr_distributor']}")
        if embed.get("mpr_category"):
            st.caption(f"Category: {embed['mpr_category']}")
    elif variant == "ipr":
        st.caption(embed.get("ipr_caption") or "")

    full_json = embed.get("full_list_json")
    if full_json:
        st.dataframe(
            _df_from_json_records(full_json),
            use_container_width=True,
            height=CHAT_PRODUCTS_TABLE_HEIGHT,
            key=f"versa_chat_full_{key_suffix}",
        )
    else:
        st.write("No full list available.")
