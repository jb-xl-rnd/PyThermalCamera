# File: main.py

import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
import cv2
from thermal_camera import ThermalCamera
from utils import print_info, wait_for_device
import threading
import queue
import time

# Global state - initialized at startup, not module load
camera = None
frame_queue = queue.Queue(maxsize=1)
camera_thread_handle = None
shutdown_event = threading.Event()

DEVICE_PATH = '/dev/video0'
DEVICE_TIMEOUT = 120  # seconds to wait for camera device


def init_camera_with_retry(max_retries=5, retry_delay=3):
    """Initialize camera with retry logic."""
    global camera

    for attempt in range(max_retries):
        try:
            print(f"Camera init attempt {attempt + 1}/{max_retries}")
            camera = ThermalCamera()
            print("Camera initialized successfully")
            return True
        except Exception as e:
            print(f"Camera init failed: {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay}s...")
                time.sleep(retry_delay)

    print("Failed to initialize camera after all retries")
    return False


def camera_loop():
    """Main camera processing loop."""
    global camera
    print_info()

    while not shutdown_event.is_set():
        if camera is None:
            time.sleep(1)
            continue

        try:
            frame = camera.process_frame()
            if frame is None:
                print("Camera returned None frame, reinitializing...")
                time.sleep(2)
                init_camera_with_retry(max_retries=3)
                continue

            # Replace old frame in queue (drop if full)
            if not frame_queue.empty():
                try:
                    frame_queue.get_nowait()
                except queue.Empty:
                    pass
            frame_queue.put(frame)

            camera.update_elapsed_time()

            if camera.settings.recording:
                camera.videoOut.write(frame)

        except Exception as e:
            print(f"Error in camera loop: {e}")
            time.sleep(1)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown."""
    global camera_thread_handle

    print(f"Waiting for camera device {DEVICE_PATH}...")
    if not wait_for_device(DEVICE_PATH, timeout=DEVICE_TIMEOUT):
        print(f"Warning: Device {DEVICE_PATH} not found, will retry during operation")

    # Small delay after device appears to let it stabilize
    time.sleep(2)

    if not init_camera_with_retry():
        print("Warning: Camera not available at startup, will retry")

    # Start camera thread
    shutdown_event.clear()
    camera_thread_handle = threading.Thread(target=camera_loop, daemon=True)
    camera_thread_handle.start()
    print("Camera thread started")

    yield  # App is running

    # Shutdown
    print("Shutting down...")
    shutdown_event.set()
    if camera is not None:
        camera.close()
    print("Shutdown complete")


app = FastAPI(lifespan=lifespan)


def gen_frames():
    """Generate MJPEG frames for streaming."""
    while not shutdown_event.is_set():
        try:
            # Use timeout to allow checking shutdown_event
            frame = frame_queue.get(timeout=1.0)
            _, buffer = cv2.imencode('.jpg', frame)
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        except queue.Empty:
            # No frame available, continue waiting
            continue
        except Exception as e:
            print(f"Error encoding frame: {e}")
            continue


@app.get("/")
async def index():
    return HTMLResponse("""
    <html>
        <head>
            <title>Thermal Camera Stream</title>
            <style>
                body {
                    margin: 0;
                    padding: 0;
                    display: flex;
                    height: 100vh;
                }
                .video-container {
                    flex: 1;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                }
                .button-container {
                    width: 200px;
                    padding: 20px;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                }
                button {
                    margin-bottom: 10px;
                    padding: 10px;
                    width: 100%;
                }
            </style>
        </head>
        <body>
            <div class="video-container">
                <img src="/video_feed" width="640" height="480" />
            </div>
            <div class="button-container">
                <button onclick="sendCommand('m')">Cycle Colormap</button>
                <button onclick="sendCommand('h')">Toggle HUD</button>
                <button onclick="sendCommand('r')">Start/Stop Recording</button>
                <button onclick="sendCommand('p')">Take Snapshot</button>
                <button onclick="sendCommand('f')">Contrast +</button>
                <button onclick="sendCommand('v')">Contrast -</button>
            </div>
            <script>
                function sendCommand(cmd) {
                    fetch('/command/' + cmd)
                        .then(response => response.json())
                        .then(data => console.log(data));
                }
            </script>
        </body>
    </html>
    """)


@app.get("/video_feed")
async def video_feed():
    return StreamingResponse(gen_frames(), media_type="multipart/x-mixed-replace; boundary=frame")


@app.get("/command/{cmd}")
async def execute_command(cmd: str):
    if camera is None:
        return {"status": "error", "message": "Camera not initialized"}
    camera.handle_command(cmd)
    return {"status": "success", "command": cmd}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy" if camera is not None else "degraded",
        "camera_initialized": camera is not None,
        "queue_size": frame_queue.qsize()
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
