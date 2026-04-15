"""
Remove generated deck files (presentation_<uuid>.pptx) after a TTL on disk.

Streamlit session state does not delete files when a session ends; this keeps the
configured save directories from growing without bound on shared hosts (e.g. DigitalOcean).
"""
from __future__ import annotations

import logging
import os
import time
from pathlib import Path

logger = logging.getLogger(__name__)

_DEFAULT_TTL_SECONDS = 25 * 60
_MIN_TTL_SECONDS = 60
_MIN_CLEANUP_INTERVAL_SEC = 60.0
_last_cleanup_monotonic: float | None = None


def _read_ttl_seconds() -> int:
    """
    TTL in seconds for generated decks. 0 = disabled (no cleanup).

    Config (first match wins):
    - [downloads] deck_ttl_seconds in secrets.toml (0 disables)
    - [downloads] deck_ttl_minutes in secrets.toml (0 disables)
    - Env VERSA_DECK_TTL_MINUTES (0 disables; empty falls through to default)
    """
    try:
        import streamlit as st

        if "downloads" not in st.secrets:
            return _DEFAULT_TTL_SECONDS
        d = st.secrets["downloads"]
        if "deck_ttl_seconds" in d and d["deck_ttl_seconds"] is not None:
            v = int(d["deck_ttl_seconds"])
            return 0 if v <= 0 else max(_MIN_TTL_SECONDS, v)
        if "deck_ttl_minutes" in d and d["deck_ttl_minutes"] is not None:
            m = float(d["deck_ttl_minutes"])
            if m <= 0:
                return 0
            return max(_MIN_TTL_SECONDS, int(m * 60))
    except (TypeError, ValueError, KeyError, AttributeError, Exception):
        pass

    env = (os.environ.get("VERSA_DECK_TTL_MINUTES") or "").strip()
    if env:
        try:
            m = float(env)
            if m <= 0:
                return 0
            return max(_MIN_TTL_SECONDS, int(m * 60))
        except ValueError:
            pass

    return _DEFAULT_TTL_SECONDS


def _iter_deck_directories() -> list[Path]:
    """Directories where PPR/IPR save presentation_<uuid>.pptx files."""
    from src.utils.versa_paths import get_versa_downloads_dir

    dirs: list[Path] = [get_versa_downloads_dir()]

    try:
        import streamlit as st

        raw = (st.secrets["downloads"]["deck_saving_path"] or "").strip()
        if raw:
            p = Path(raw.replace("\\", "/").rstrip("/"))
            if p.is_dir():
                dirs.append(p.resolve())
    except (KeyError, TypeError, AttributeError, Exception):
        pass

    ppr_env = (os.environ.get("PPR_DECK_SAVING_PATH") or "").strip()
    if ppr_env:
        p = Path(ppr_env.replace("\\", "/").rstrip("/"))
        if p.is_dir():
            dirs.append(p.resolve())

    seen: set[str] = set()
    out: list[Path] = []
    for d in dirs:
        try:
            key = str(d.resolve())
        except OSError:
            key = str(d)
        if key not in seen:
            seen.add(key)
            out.append(d)
    return out


def cleanup_expired_generated_decks(*, force: bool = False) -> int:
    """
    Delete presentation_*.pptx files older than the configured TTL.

    Throttled to at most once per MIN_CLEANUP_INTERVAL_SEC unless force=True
    (e.g. right after building a deck).

    Returns the number of files removed.
    """
    global _last_cleanup_monotonic

    now = time.monotonic()
    if not force and _last_cleanup_monotonic is not None:
        if (now - _last_cleanup_monotonic) < _MIN_CLEANUP_INTERVAL_SEC:
            return 0
    _last_cleanup_monotonic = now

    ttl = _read_ttl_seconds()
    if ttl <= 0:
        return 0

    cutoff = time.time() - ttl
    removed = 0

    for d in _iter_deck_directories():
        if not d.is_dir():
            continue
        try:
            with os.scandir(d) as it:
                for entry in it:
                    if not entry.is_file():
                        continue
                    name = entry.name
                    if not (name.startswith("presentation_") and name.endswith(".pptx")):
                        continue
                    try:
                        if entry.stat().st_mtime < cutoff:
                            os.unlink(entry.path)
                            removed += 1
                    except OSError as e:
                        logger.debug("Deck TTL: could not remove %s: %s", entry.path, e)
        except OSError as e:
            logger.warning("Deck TTL: could not scan %s: %s", d, e)

    if removed:
        logger.info("Deck TTL cleanup removed %s file(s) older than %s s", removed, ttl)
    return removed
