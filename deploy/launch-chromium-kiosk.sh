#!/bin/bash

# Wait for the thermal camera API to be ready
echo "Waiting for thermal camera API..."
MAX_WAIT=120
WAITED=0
while [ $WAITED -lt $MAX_WAIT ]; do
    if curl -s http://127.0.0.1:8000/health > /dev/null 2>&1; then
        echo "API is ready after ${WAITED}s"
        break
    fi
    sleep 2
    WAITED=$((WAITED + 2))
    echo "Waiting for API... (${WAITED}s)"
done

if [ $WAITED -ge $MAX_WAIT ]; then
    echo "Warning: API not ready after ${MAX_WAIT}s, launching anyway"
fi

sleep 2

# Launch Chromium in kiosk mode
# Note: --disable-gpu and --no-sandbox are required for stability on Pi 5
# GPU acceleration causes crashes, software rendering is used instead
exec chromium-browser \
    --kiosk \
    --start-fullscreen \
    --start-maximized \
    --disable-gpu \
    --disable-software-rasterizer \
    --no-sandbox \
    --disable-dev-shm-usage \
    --app=http://127.0.0.1:8000
