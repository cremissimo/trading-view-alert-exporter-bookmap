#!/bin/bash
set -e

echo "Starting Trading View Email Monitor with cron and HTTP server..."
echo "Cron daemon running as: $(whoami)"
echo "Python script running as: appuser"
echo "Cron schedule: Every 2 minutes"
echo "HTTP server: http://localhost:8000"
echo "----------------------------------------"

# Start HTTP server in background as appuser (output to stdout/stderr)
echo "Starting HTTP server..."
su - appuser -c "cd /app/notes && /usr/bin/python3 -m http.server 8000" &

# Run the script once immediately on startup as appuser (output to stdout/stderr)
echo "Running initial check..."
su - appuser -c "cd /app && /usr/bin/python3 __main__.py"

# Start cron in foreground
echo "Starting cron service..."
cron -f
