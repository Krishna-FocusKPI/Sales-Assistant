"""
Shared paths for .versa/workflows cache files.
Use this instead of hard-coded '/.versa/workflows/...' so paths work on all systems.

Docker / entrypoint stores workflow files under `/.versa/workflows`. Set env VERSA_DATA_ROOT=/.versa
so lookups match (see Dockerfile). Locally, omit VERSA_DATA_ROOT to use <project>/.versa/...
"""
import logging
import os
from pathlib import Path
from typing import Any, Optional

import pandas as pd

logger = logging.getLogger(__name__)


def get_project_root() -> Path:
    """Project root (VERSA directory). Assumes this file is at src/utils/versa_paths.py."""
    return Path(__file__).resolve().parent.parent.parent


def get_versa_data_root() -> Path:
    """
    Root for runtime .versa data (workflows pick/CSV, downloads, etc.).
    VERSA_DATA_ROOT overrides (e.g. /.versa in Docker); default is <project>/.versa.
    """
    override = (os.environ.get("VERSA_DATA_ROOT") or "").strip()
    if override:
        return Path(override)
    return get_project_root() / ".versa"


def get_workflow_cache_path(filename: str) -> Path:
    """Path to a file under <versa_data_root>/workflows/<filename>."""
    return get_versa_data_root() / "workflows" / filename


def get_versa_downloads_dir() -> Path:
    """Directory for generated decks / downloads under the same versa root."""
    return get_versa_data_root() / "downloads"


def resolve_saved_deck_path(workflow_memory: Any) -> Optional[Path]:
    """
    Path to the last built .pptx for PPR/IPR, if the file exists.
    Prefer workflow_memory.deck_path when set; else <versa>/downloads/<deck_name>.
    """
    if workflow_memory is None:
        return None
    saved = getattr(workflow_memory, "deck_path", None)
    if saved:
        p = Path(str(saved))
        if p.is_file():
            return p
    name = getattr(workflow_memory, "deck_name", None)
    if not name:
        return None
    p = get_versa_downloads_dir() / str(name)
    return p if p.is_file() else None


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
