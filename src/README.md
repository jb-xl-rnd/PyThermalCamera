# Thermal Camera FastAPI Application

This application provides a web interface for controlling and viewing the output of a Topdon TC001 Thermal camera. It uses FastAPI to serve the camera feed and handle user commands, making the thermal camera accessible through a web browser.

## Features

- Live streaming of thermal camera feed
- Adjustable contrast
- Colormap cycling
- HUD toggle
- Recording start/stop
- Snapshot capability
- Responsive web interface

## Files

The application consists of the following files:

1. `main.py`: The FastAPI application entry point. It sets up the web server, defines routes, and manages the camera thread. This file is responsible for:
   - Initializing the FastAPI app
   - Setting up the camera thread
   - Defining API endpoints for the web interface
   - Handling video streaming and command processing

2. `thermal_camera.py`: Contains the `ThermalCamera` class, which interfaces with the physical camera and processes frames. Key responsibilities include:
   - Initializing and managing the camera connection
   - Processing raw camera data into heatmap images
   - Handling camera settings and commands (e.g., changing colormap, adjusting contrast)
   - Managing recording and snapshot functionalities

3. `settings.py`: Defines the `CameraSettings` dataclass used to store camera configuration. It includes:
   - Default values for camera parameters (width, height, scale, etc.)
   - A property method to calculate new dimensions based on the scale

4. `utils.py`: Contains utility functions used throughout the application, including:
   - `COLORMAPS`: A list of available color maps for the thermal image
   - `is_raspberrypi()`: Checks if the code is running on a Raspberry Pi
   - Temperature calculation functions
   - `draw_text()`: A function for drawing text on images
   - `print_info()`: Prints information about the application and its controls

5. `__pycache__/`: A directory created by Python to store compiled bytecode for faster loading.

6. `20241015--202341output.avi`: An example of a recorded video output file (the exact filename will vary).

7. `TC00120241015-202338.png`: An example of a snapshot image file (the exact filename will vary).

## Setup

1. Ensure you have Python 3.7+ installed on your system.

2. Install the required dependencies:
   ```
   pip install fastapi uvicorn opencv-python numpy
   ```

3. Connect the Topdon TC001 Thermal camera to your device.

## Usage

1. Navigate to the project directory in your terminal.

2. Run the application:
   ```
   python3 main.py
   ```

3. Open a web browser and go to `http://localhost:8000` (or the IP address of your device if accessing remotely).

4. You should see the thermal camera feed and control buttons on the web page.

5. Use the buttons to control various aspects of the camera:
   - "Cycle Colormap": Changes the color scheme of the thermal image
   - "Toggle HUD": Shows/hides the heads-up display with camera information
   - "Start/Stop Recording": Begins or ends video recording
   - "Take Snapshot": Captures a still image
   - "Contrast +": Increases image contrast
   - "Contrast -": Decreases image contrast

## Accessing Remotely

To access the application from another device on the same network:

1. Find the IP address of the device running the application.
   - On Linux/Mac, you can use the `ifconfig` command.
   - On Windows, use the `ipconfig` command.

2. On the remote device, open a web browser and navigate to `http://<IP_ADDRESS>:8000`, replacing `<IP_ADDRESS>` with the actual IP address of the device running the application.

## Notes

- This application is designed for use with the Topdon TC001 Thermal camera. Other thermal cameras may not be compatible without modifications.
- The application uses port 8000 by default. Ensure this port is not in use by another application.
- For security reasons, it's recommended to use this application only on trusted networks.
- The `print_info()` function in `utils.py` displays information about key bindings, which are not directly used in the web interface but reflect the original functionality of the application.

## Output Files

- Recorded videos are saved as AVI files with names in the format `YYYYMMDD--HHMMSSoutput.avi`.
- Snapshots are saved as PNG files with names in the format `TC001YYYYMMDD-HHMMSS.png`.

## Troubleshooting

If you encounter issues:

1. Ensure all dependencies are correctly installed.
2. Check that the thermal camera is properly connected and recognized by your system.
3. Verify that no other application is using the camera or the specified port.
4. Check the console output for any error messages or exceptions.

For further assistance, please open an issue on the project's GitHub repository.

## Credits

This application was originally developed by Les Wright and has been adapted for web-based usage with FastAPI.