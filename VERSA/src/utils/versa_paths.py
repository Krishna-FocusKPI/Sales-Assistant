"""
Shared paths for .versa/workflows cache files.
Use this instead of hard-coded '/.versa/workflows/...' so paths work on all systems.
"""
import logging
import os
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


def get_project_root() -> Path:
    """Project root (VERSA directory). Assumes this file is at src/utils/versa_paths.py."""
    return Path(__file__).resolve().parent.parent.parent


def get_workflow_cache_path(filename: str) -> Path:
    """Path to a file under project_root/.versa/workflows/<filename>."""
    return get_project_root() / ".versa" / "workflows" / filename


def resolve_workflow_path(path_or_filename: str) -> str:
    """
    Resolve a path from config (e.g. '/.versa/workflows/ppr_template.pptx' or 'ppr_template.pptx')
    to an absolute path under project .versa/workflows, so it works on Windows and Linux.
    Returns empty string if the resolved file does not exist.
    """
    path = (path_or_filename or "").strip().replace("\\", "/")
    if not path:
        return ""
    # /.versa/workflows/foo.pptx or .versa/workflows/foo.pptx -> project .versa/workflows
    if ".versa/workflows/" in path or path.startswith("/.versa/") or path.startswith(".versa/"):
        filename = path.split("workflows/")[-1].split("/")[0] or path
        resolved = get_workflow_cache_path(filename)
        return str(resolved) if resolved.is_file() else ""
    # Just filename (e.g. ppr_template.pptx)
    if "/" not in path:
        resolved = get_workflow_cache_path(path)
        return str(resolved) if resolved.is_file() else ""
    # Absolute path that exists
    if os.path.isfile(path):
        return path
    # Relative path from project root
    root = get_project_root()
    resolved = (root / path.lstrip("/")).resolve()
    return str(resolved) if resolved.is_file() else ""


def load_workflow_pickle(filename: str, *, empty_if_missing: bool = True):
    """
    Load a pickle file from .versa/workflows/<filename>.
    If empty_if_missing is True and the file does not exist, return an empty DataFrame
    and log a warning (so the app can start without client cache files).
    If empty_if_missing is False, raise FileNotFoundError when missing.
    """
    path = get_workflow_cache_path(filename)
    if path.exists():
        return pd.read_pickle(path)
    if empty_if_missing:
        logger.warning("Cache file not found %s; using empty DataFrame. Add the file or use Snowflake to populate.", path)
        return pd.DataFrame()
    raise FileNotFoundError(f"Cache file not found: {path}")


def load_workflow_csv(filename: str, *, empty_if_missing: bool = True):
    """
    Load a CSV file from .versa/workflows/<filename>.
    If empty_if_missing is True and the file does not exist, return an empty DataFrame.
    """
    path = get_workflow_cache_path(filename)
    if path.exists():
        return pd.read_csv(path)
    if empty_if_missing:
        logger.warning("Cache file not found %s; using empty DataFrame.", path)
        return pd.DataFrame()
    raise FileNotFoundError(f"Cache file not found: {path}")
