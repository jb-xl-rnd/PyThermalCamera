# PyThermalcam
Python Software to use the Topdon TC001 Thermal Camera on Linux and the Raspberry Pi. It **may** work with other similar cameras! Please feed back if it does!

Huge kudos to LeoDJ on the EEVBlog forum for reverse engineering the image format from these kind of cameras (InfiRay P2 Pro) to get the raw temperature data!
https://www.eevblog.com/forum/thermal-imaging/infiray-and-their-p2-pro-discussion/200/
Check out Leo's Github here: https://github.com/LeoDJ/P2Pro-Viewer/tree/main

## Introduction

This is a quick and dirty Python implementation of Thermal Camera software for the Topdon TC001!
(https://www.amazon.co.uk/dp/B0BBRBMZ58)
No commands are sent the the camera, instead, we take the raw video feed, do some openCV magic, and display a nice heatmap along with relevant temperature points highlighted.

![Screenshot](media/TC00120230701-131032.png)

This program, and associated information is Open Source (see Licence), but if you have gotten value from these kinds of projects and think they are worth something, please consider donating: https://paypal.me/leslaboratory?locale.x=en_GB

This readme is accompanied by youtube videos. Visit my Youtube Channel at: https://www.youtube.com/leslaboratory

The video is here: https://youtu.be/PiVwZoQ8_jQ

## Features

Tested on Debian all features are working correctly This has been tested on the Pi However a number of workarounds are implemented! Seemingly there are bugs in the compiled version of openCV that ships with the Pi!!

The following features have been implemented:

<img align="right" src="media/colormaps.png">

- Bicubic interpolation to scale the small 256*192 image to something more presentable! Available scaling multiplier range from 1-5 (Note: This will not auto change the window size on the Pi (openCV needs recompiling), however you can manually resize). Optional blur can be applied if you want to smooth out the pixels.
- Fullscreen / Windowed mode (Note going back to windowed  from fullscreen does not seem to work on the Pi! OpenCV probably needs recompiling!).
- False coloring of the video image is provided. the avilable colormaps are listed on the right.
- Variable Contrast.
- Average Scene Temperature.
- Center of scene temperature monitoring (Crosshairs).
- Floating Maximum and Minimum temperature values within the scene, with variable threshold.
- Video recording is implemented (saved as AVI in the working directory).
- Snapshot images are implemented (saved as PNG in the working directory).

The current settings are displayed in a box at the top left of the screen (The HUD):

- Avg Temperature of the scene
- Label threshold (temperature threshold at which to display floating min max values)
- Colormap
- Blur (blur radius)
- Scaling multiplier
- Contrast value
- Time of the last snapshot image
- Recording status

## Dependencies

Python3 OpenCV Must be installed:

Run: **sudo apt-get install python3-opencv**

## Running the Program

In src you will find:

**main.py** - FastAPI-based web server that streams the thermal camera feed via MJPEG. Includes a web UI with control buttons.

To run it plug in the thermal camera and run: **v4l2-ctl --list-devices** to list the devices on the system.

Then simply issue: **python3 main.py**

The web interface will be available at http://localhost:8000

### API Endpoints

- `/` - Web UI with video stream and control buttons
- `/video_feed` - MJPEG video stream
- `/command/{cmd}` - Send commands (m, h, r, p, f, v)
- `/health` - Health check endpoint

## Key Bindings (via web UI buttons)

- m : Cycle through ColorMaps
- h : Toggle HUD
- r : Start/Stop Recording
- p : Take Snapshot
- f : Contrast +
- v : Contrast -

---

## Raspberry Pi Kiosk Deployment

This section documents how to deploy the thermal camera as a dedicated kiosk on a Raspberry Pi 5.

### Known Issues & Solutions

1. **Race Condition at Boot**: The USB camera device (`/dev/video0`) may not be ready when the service starts. The code now waits up to 120 seconds for the device.

2. **Power Supply Issues**: Pi 5 with thermal camera can draw significant power. Symptoms include random crashes, SIGILL errors, and "low power event" warnings.

3. **Browser GPU Crashes**: Both Chromium and Firefox have GPU driver issues on Pi 5. Chromium works with GPU disabled (`--disable-gpu --no-sandbox`).

4. **High CPU Usage**: Software rendering without GPU causes ~40-90% CPU usage on the browser renderer.

### Deployment Files

All deployment files are in the `deploy/` folder:

- `thermal-camera-app.service` - Systemd service for the Python camera app
- `chromium-kiosk.service` - Systemd service for the kiosk browser
- `launch-chromium-kiosk.sh` - Kiosk launcher script with API wait logic
- `config.txt.additions` - Power saving settings for `/boot/firmware/config.txt`

### Installation Steps

```bash
# 1. Copy project to Pi
scp -r src/ pi@<PI_IP>:/home/pi/PyThermalCamera/

# 2. Install dependencies
ssh pi@<PI_IP> "sudo apt-get install python3-opencv python3-fastapi python3-uvicorn"

# 3. Copy and enable services
scp deploy/thermal-camera-app.service pi@<PI_IP>:/tmp/
scp deploy/chromium-kiosk.service pi@<PI_IP>:/tmp/
scp deploy/launch-chromium-kiosk.sh pi@<PI_IP>:/home/pi/

ssh pi@<PI_IP> "
  sudo mv /tmp/thermal-camera-app.service /etc/systemd/system/
  sudo mv /tmp/chromium-kiosk.service /etc/systemd/system/
  chmod +x /home/pi/launch-chromium-kiosk.sh
  sudo systemctl daemon-reload
  sudo systemctl enable thermal-camera-app.service
  sudo systemctl enable chromium-kiosk.service
"

# 4. Apply power saving settings (append to config.txt)
ssh pi@<PI_IP> "sudo cat >> /boot/firmware/config.txt" < deploy/config.txt.additions

# 5. Disable unnecessary services
ssh pi@<PI_IP> "sudo systemctl disable --now ModemManager cups cups-browsed avahi-daemon colord wpa_supplicant triggerhappy udisks2"

# 6. Reboot
ssh pi@<PI_IP> "sudo reboot"
```

### Power Saving Settings Applied

| Setting | Value | Effect |
|---------|-------|--------|
| arm_freq | 1500 MHz | CPU underclocked from 2400 MHz |
| gpu_freq | 400 MHz | GPU underclocked from 1000 MHz |
| over_voltage | -4 | Reduced voltage |
| arm_boost | 0 | Turbo boost disabled |
| WiFi/BT | disabled | Radios off |
| LEDs | disabled | Activity LEDs off |

### Services Disabled

- ModemManager, cups, cups-browsed, avahi-daemon, colord
- wpa_supplicant, triggerhappy, udisks2, accounts-daemon

### Troubleshooting

**Camera not detected:**
```bash
# Check if device exists
ls -la /dev/video*
# Check service logs
journalctl -u thermal-camera-app.service -f
```

**Browser not displaying:**
```bash
# Check kiosk logs
journalctl -u chromium-kiosk.service -f
# Test API manually
curl http://127.0.0.1:8000/health
```

**Power issues:**
```bash
# Check throttling status
vcgencmd get_throttled
# 0x0 = OK, other values indicate power/thermal issues
```

---

## TODO:

- Investigate GPU acceleration options for reduced CPU usage
- Consider direct display mode (pygame/OpenCV) instead of browser for efficiency
- Add temperature logging/graphing features
- Implement error recovery for camera disconnection
