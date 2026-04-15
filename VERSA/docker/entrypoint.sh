#!/bin/bash

# Path to the data directory (Docker volume on Droplet, or local dir on App Platform)
DATA_PATH="/.versa"
if [ ! -d "$DATA_PATH" ]; then
    echo "Creating $DATA_PATH (ephemeral unless a volume is mounted)."
    mkdir -p "$DATA_PATH"
fi

# Create subdirectories for dags
DAG_PATH=$DATA_PATH/dags
if [ -d "$DAG_PATH" ]; then
    echo "Found folder for image at $DAG_PATH."
else
    echo "No folder for image found. Setting up $DAG_PATH..."
    # Create the data directory if it doesn't exist
    mkdir $DAG_PATH
fi

# Create subdirectories for logs
LOG_PATH=$DATA_PATH/logs
if [ -d "$LOG_PATH" ]; then
    echo "Found folder for logs at $LOG_PATH."
else
    echo "No folder for logs found. Setting up $LOG_PATH..."
    # Create the data directory if it doesn't exist
    mkdir $LOG_PATH
fi

# Create subdirectories for workflows
WORKFLOW_PATH=$DATA_PATH/workflows
if [ -d "$WORKFLOW_PATH" ]; then
    echo "Found folder for workflows at $WORKFLOW_PATH."
else
    echo "No folder for workflows found. Setting up $WORKFLOW_PATH..."
    # Create the data directory if it doesn't exist
    mkdir $WORKFLOW_PATH
    mv /app/workflows/* $WORKFLOW_PATH
fi

# Secrets: App Platform / CI often inject VERSA_STREAMLIT_SECRETS_B64 (base64 of full secrets.toml)
CONFIG_PATH=$DATA_PATH/secrets.toml
if [ -n "${VERSA_STREAMLIT_SECRETS_B64:-}" ]; then
    echo "Writing /app/.streamlit/secrets.toml from VERSA_STREAMLIT_SECRETS_B64"
    # Strip CR/LF from pasted env values (common in dashboards) so base64 decodes correctly
    _b64=$(printf '%s' "${VERSA_STREAMLIT_SECRETS_B64}" | tr -d '\n\r')
    if ! printf '%s' "$_b64" | base64 -d > /app/.streamlit/secrets.toml; then
        echo "ERROR: VERSA_STREAMLIT_SECRETS_B64 could not be base64-decoded."
        exit 1
    fi
elif [ -f "$CONFIG_PATH" ]; then
    echo "File secrets.toml exists at $CONFIG_PATH. Replacing image default."
    cp "$CONFIG_PATH" /app/.streamlit/secrets.toml
else
    echo "No VERSA_STREAMLIT_SECRETS_B64 and no $CONFIG_PATH — using image default secrets."
fi

# Safe preview for Runtime logs (redacts api_key, passwords, tokens — never print raw secrets)
if [ -f /app/.streamlit/secrets.toml ]; then
    echo "---- /app/.streamlit/secrets.toml diagnostics (redacted) ----"
    python3 <<'PY'
from __future__ import annotations

import re
from pathlib import Path

path = Path("/app/.streamlit/secrets.toml")
raw = path.read_text(encoding="utf-8", errors="replace")
print(f"path={path} bytes={path.stat().st_size}")
sections = re.findall(r"^\s*\[([^\]]+)\]", raw, flags=re.MULTILINE)
print("sections:", sections if sections else "(none parsed)")
openai_ok = any(s.strip().lower() == "openai" for s in sections)
print("[openai] section present:", openai_ok)


def redact_line(line: str) -> str:
    m = re.match(r"^(\s*)([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+)$", line)
    if not m:
        return line.rstrip()[:220]
    key = m.group(2).lower()
    if any(
        p in key
        for p in (
            "password",
            "secret",
            "api_key",
            "token",
            "slt",
            "credential",
            "private",
        )
    ):
        return f"{m.group(1)}{m.group(2)} = <REDACTED>"
    return line.rstrip()[:220]


print("--- first 45 lines (redacted) ---")
for i, line in enumerate(raw.splitlines()[:45], 1):
    print(f"{i:3}| {redact_line(line)}")
print("---- end secrets diagnostics ----")
PY
else
    echo "WARNING: /app/.streamlit/secrets.toml missing after secrets step."
fi

# Continue with the normal execution of the container's main process
exec "$@"