#!/bin/bash

# Get current date and time in the format YYYY-MM-DD_HH-MM-SS
current_time=$(date +"%Y-%m-%d_%H-%M-%S")

# Define the log file name with the current time
log_file="/.versa/logs/running_log_${current_time}.log"

# Run your Streamlit application with stderr redirected to the log file
streamlit run run.py --server.address 0.0.0.0 --server.baseUrlPath=/salesbuilder  --logger.level=info 2> "$log_file"
