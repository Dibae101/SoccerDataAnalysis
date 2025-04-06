#!/bin/bash

# Elevate if not root
if [ "$EUID" -ne 0 ]; then
  echo "🔒 Switching to root..."
  exec sudo "$0" "$@"
fi

echo "Applying system configuration for Doris BE..."

# Apply kernel and system limits
sysctl -w vm.max_map_count=2000000
ulimit -n 655350

echo "System config:"
sysctl vm.max_map_count
echo "ulimit -n: $(ulimit -n)"

# Path to Doris BE start script and pid file
BE_DIR="/home/ubuntu/apache-doris-2.1.8.1-bin-x64/be"
PID_FILE="$BE_DIR/bin/be.pid"

# Handle leftover PID file with permission issue
if [ -f "$PID_FILE" ]; then
  echo "Removing existing BE PID file..."
  rm -f "$PID_FILE" || { echo "Failed to remove $PID_FILE. Check permissions."; exit 1; }
fi

# Start Doris BE
echo "Starting Apache Doris Backend..."
$BE_DIR/bin/start_be.sh --daemon