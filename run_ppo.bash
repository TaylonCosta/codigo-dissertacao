#!/bin/bash

# Path to your Python script
PYTHON_SCRIPT="main.py"

# Define parameters
PARAMS="--ppo"

# Infinite loop to restart the script if it crashes
while true; do
    echo "Starting Python script with parameters: $PARAMS"
    python3 "$PYTHON_SCRIPT" $PARAMS
    
    # Check the exit code of the Python script
    EXIT_CODE=$?
    if [ $EXIT_CODE -eq 0 ]; then
        echo "Python script finished successfully."
        break
    else
        echo "Python script crashed with exit code $EXIT_CODE. Restarting..."
        sleep 5  # Pause for 5 seconds before restarting
    fi
done
