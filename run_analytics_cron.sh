#!/bin/bash

#
# Business Broker Analytics - Cron Job Wrapper
# ============================================
#
# This script orchestrates the analytics process for cron job execution:
# 1. Runs the analytics script
# 2. Captures the output
# 3. Updates Apple Notes with the results
# 4. Handles logging and error cases
#
# Usage:
#   ./run_analytics_cron.sh [hours] [mode]
#
# Arguments:
#   hours: Number of hours to analyze (default: 24)
#   mode:  'manual' for manual testing, 'dryrun' for testing without Notes update
#

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ANALYTICS_SCRIPT="$SCRIPT_DIR/analytics_for_notes.py"
# APPLESCRIPT_FILE removed - using Python-based Notes updater
LOG_DIR="$SCRIPT_DIR/logs"
LOG_FILE="$LOG_DIR/analytics_cron.log"
NOTES_LOG_FILE="$LOG_DIR/notes_update.log"

# Create logs directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Function to log messages with timestamp
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Function to log errors
log_error() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - ERROR: $1" | tee -a "$LOG_FILE" >&2
}

# Parse arguments
HOURS=${1:-24}
MODE=${2:-""}

# Validate hours argument
if ! [[ "$HOURS" =~ ^[0-9]+$ ]]; then
    log_error "Invalid hours argument: $HOURS. Must be a positive integer."
    exit 1
fi

# Set up environment for cron
export PATH="/usr/local/bin:/usr/bin:/bin:$PATH"
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"

# Change to script directory to ensure relative paths work
cd "$SCRIPT_DIR" || {
    log_error "Failed to change to script directory: $SCRIPT_DIR"
    exit 1
}

# Activate virtual environment if it exists
if [[ -f ".venv/bin/activate" ]]; then
    source ".venv/bin/activate"
    log_message "Activated virtual environment"
elif [[ -f "venv/bin/activate" ]]; then
    source "venv/bin/activate"
    log_message "Activated virtual environment"
fi

log_message "Starting analytics cron job (Hours: $HOURS, Mode: $MODE)"

# Check if required files exist
if [[ ! -f "$ANALYTICS_SCRIPT" ]]; then
    log_error "Analytics script not found: $ANALYTICS_SCRIPT"
    exit 1
fi

# AppleScript file check removed - using Python-based Notes updater

if [[ ! -f "config.env" ]]; then
    log_error "Configuration file not found: config.env"
    exit 1
fi

# Check Python availability
if ! command -v python3 &> /dev/null; then
    log_error "Python3 not found in PATH"
    exit 1
fi

# Run the analytics script and capture output
log_message "Running analytics script for $HOURS hours..."

ANALYTICS_OUTPUT=$(python3 "$ANALYTICS_SCRIPT" "$HOURS" 2>&1)
ANALYTICS_EXIT_CODE=$?

if [[ $ANALYTICS_EXIT_CODE -ne 0 ]]; then
    log_error "Analytics script failed with exit code $ANALYTICS_EXIT_CODE"
    log_error "Output: $ANALYTICS_OUTPUT"
    
    # Create error report for Notes
    ERROR_REPORT="ANALYTICS SCRIPT ERROR
$(date '+%Y-%m-%d %H:%M:%S UTC')

Exit code: $ANALYTICS_EXIT_CODE
Output: $ANALYTICS_OUTPUT

======================================================================"
    
    # Update Notes with error report if not in dry run mode
    if [[ "$MODE" != "dryrun" ]]; then
        log_message "Updating Notes with error report..."
        osascript "$APPLESCRIPT_FILE" "$ERROR_REPORT" >> "$NOTES_LOG_FILE" 2>&1
    fi
    
    exit 1
fi

log_message "Analytics script completed successfully"

# Check if we have content to add to Notes
if [[ -z "$ANALYTICS_OUTPUT" ]]; then
    log_error "Analytics script produced no output"
    exit 1
fi

# Handle different modes
case "$MODE" in
    "manual")
        log_message "Manual mode: Displaying output instead of updating Notes"
        echo "=== ANALYTICS OUTPUT ==="
        echo "$ANALYTICS_OUTPUT"
        echo "========================"
        ;;
    "dryrun")
        log_message "Dry run mode: Not updating Notes"
        echo "Would update Notes with:"
        echo "------------------------"
        echo "$ANALYTICS_OUTPUT"
        echo "------------------------"
        ;;
    *)
        # Normal mode: Update Notes
        log_message "Updating Apple Notes..."
        
        # Use Python-based Notes updater for better line break handling
        APPLESCRIPT_OUTPUT=$(python3 "$SCRIPT_DIR/update_notes.py" "$ANALYTICS_OUTPUT" 2>&1)
        APPLESCRIPT_EXIT_CODE=$?
        
        # Log AppleScript output
        echo "$(date '+%Y-%m-%d %H:%M:%S') - $APPLESCRIPT_OUTPUT" >> "$NOTES_LOG_FILE"
        
        if [[ $APPLESCRIPT_EXIT_CODE -ne 0 ]]; then
            log_error "Failed to update Notes. AppleScript exit code: $APPLESCRIPT_EXIT_CODE"
            log_error "AppleScript output: $APPLESCRIPT_OUTPUT"
            exit 1
        fi
        
        log_message "Successfully updated Apple Notes"
        ;;
esac

# Clean up old log files (keep last 30 days)
find "$LOG_DIR" -name "*.log" -type f -mtime +30 -delete 2>/dev/null

log_message "Analytics cron job completed successfully"

# Output summary for cron email notifications (if enabled)
if [[ "$MODE" == "" ]]; then
    echo "Business Broker Analytics completed at $(date)"
    echo "Hours analyzed: $HOURS"
    echo "Notes updated successfully"
fi

exit 0 