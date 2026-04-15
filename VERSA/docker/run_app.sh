#!/bin/bash

# Get current date and time in the format YYYY-MM-DD_HH-MM-SS
current_time=$(date +"%Y-%m-%d_%H-%M-%S")

# Define the log file name with the current time
log_file="/.versa/logs/running_log_${current_time}.log"

# App Platform / most hosts: leave VERSA_BASE_URL_PATH unset → serve at /. Legacy nginx subpath: set VERSA_BASE_URL_PATH=/salesbuilder
if [ -n "${VERSA_BASE_URL_PATH:-}" ]; then
  streamlit run run.py --server.address 0.0.0.0 --server.baseUrlPath="${VERSA_BASE_URL_PATH}" --logger.level=info 2> "$log_file"
else
  streamlit run run.py --server.address 0.0.0.0 --logger.level=info 2> "$log_file"
fi
