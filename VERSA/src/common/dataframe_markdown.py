"""Serialize DataFrames to markdown tables for chat / docs."""

from __future__ import annotations

import pandas as pd


def _escape_md_cell(s: str) -> str:
    if not isinstance(s, str):
        s = str(s)
    return s.replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ")


def dataframe_to_markdown_table(df: pd.DataFrame | None) -> str:
    """Full table as a pipe markdown table (all rows and columns)."""
    if df is None or (hasattr(df, "empty") and df.empty):
        return "_No product rows._"
    cols = list(df.columns)
    header = "| " + " | ".join(_escape_md_cell(str(c)) for c in cols) + " |"
    sep = "| " + " | ".join("---" for _ in cols) + " |"
    lines = [header, sep]
    for _, row in df.iterrows():
        cells = []
        for c in cols:
            v = row.get(c, "")
            if pd.isna(v):
                v = ""
            cells.append(_escape_md_cell(str(v)))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)
