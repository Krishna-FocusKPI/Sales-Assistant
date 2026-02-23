#!/bin/bash

# Path to the data directory
DATA_PATH="/.versa"

# Check if the data path is empty
if [ -d "$DATA_PATH" ]; then
    echo "Mounted volume found at $DATA_PATH. Creating subdirectories..."
else
    echo "No mounted volume found. Exiting..."
    # Create the data directory if it doesn't exist
    exit 1
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

#
CONFIG_PATH=$DATA_PATH/secrets.toml
if [ -f "$CONFIG_PATH" ]; then
    echo "File secrets.toml exists. Replacing current config."
    # Copy the file from /data/folder/secrets.toml to the destination
    cp $CONFIG_PATH /app/.streamlit/secrets.toml
else
    echo "File secrets.toml not found. Using default config."
fi


# Continue with the normal execution of the container's main process
exec "$@"