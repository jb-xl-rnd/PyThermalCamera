# Raspberry Pi Kiosk Setup

This project sets up a Raspberry Pi to run a thermal camera application and display its output in a full-screen Chrome browser window (kiosk mode). The setup consists of two main services:

1. Thermal Camera Application Service
2. Chromium Kiosk Service

## Services

### 1. Thermal Camera Application Service

This service runs a Python application that captures data from a thermal camera and serves it via a web interface.

- **Service Name**: `thermal-camera-app.service`
- **Main Script**: `/home/pi/PyThermalCamera/new/PyThermalCamera/src/main.py`
- **Port**: 8000

### 2. Chromium Kiosk Service

This service launches Chromium in kiosk mode, displaying the thermal camera web interface full-screen.

- **Service Name**: `chromium-kiosk.service`
- **Launch Script**: `/home/pi/launch-chromium-kiosk.sh`

## File Locations

1. **Thermal Camera Application**:
   - Main script: `/home/pi/PyThermalCamera/new/PyThermalCamera/src/main.py`
   - Service file: `/etc/systemd/system/thermal-camera-app.service`

2. **Chromium Kiosk**:
   - Launch script: `/home/pi/launch-chromium-kiosk.sh`
   - Service file: `/etc/systemd/system/chromium-kiosk.service`

## Setup Instructions

1. Ensure the thermal camera application is installed and configured correctly.

2. Copy the service files to the appropriate locations:
   ```
   sudo cp thermal-camera-app.service /etc/systemd/system/
   sudo cp chromium-kiosk.service /etc/systemd/system/
   ```

3. Make the launch script executable:
   ```
   sudo chmod +x /home/pi/launch-chromium-kiosk.sh
   ```

4. Reload systemd, enable and start the services:
   ```
   sudo systemctl daemon-reload
   sudo systemctl enable thermal-camera-app.service
   sudo systemctl enable chromium-kiosk.service
   sudo systemctl start thermal-camera-app.service
   sudo systemctl start chromium-kiosk.service
   ```

5. Reboot the Raspberry Pi to ensure everything starts correctly:
   ```
   sudo reboot
   ```

## Troubleshooting

- Check the status of the services:
  ```
  sudo systemctl status thermal-camera-app.service
  sudo systemctl status chromium-kiosk.service
  ```

- View the logs:
  ```
  sudo journalctl -u thermal-camera-app.service -f
  sudo journalctl -u chromium-kiosk.service -f
  ```

- Ensure the thermal camera application is accessible at `http://127.0.0.1:8000`

- If using a built-in display, check `/boot/config.txt` for any necessary display-specific configurations.

## Notes

- The setup is configured to work with both HDMI and the official Raspberry Pi Touch Display.
- For touch displays, an on-screen keyboard can be installed: `sudo apt install matchbox-keyboard`

For any issues or further customization, please refer to the individual service and script files.