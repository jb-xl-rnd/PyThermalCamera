#!/bin/bash

# Set up the environment
export DISPLAY=:0
export XAUTHORITY=/home/pi/.Xauthority
export XDG_RUNTIME_DIR=/run/user/1000

# Function to launch Chromium
launch_chromium() {
    # Add touch support, adjust window size, and set zoom level
    chromium-browser --kiosk --touch-events=enabled --window-size=800,480 --force-device-scale-factor=3.0 --no-first-run --noerrdialogs --disable-infobars --disable-features=TranslateUI --app=http://127.0.0.1:8000
}

# Use startx to launch a new X session with Chromium
startx /usr/bin/openbox-session -- :0 vt7 &

# Wait for X server to start
sleep 5

# Launch Chromium
DISPLAY=:0 launch_chromium