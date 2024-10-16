# File: main.py

import uvicorn
from fastapi import FastAPI, Response
from fastapi.responses import HTMLResponse, StreamingResponse
import cv2
import numpy as np
from thermal_camera import ThermalCamera
from utils import print_info
import threading
import queue

app = FastAPI()
camera = ThermalCamera()
frame_queue = queue.Queue(maxsize=1)

def camera_thread():
    print_info()
    while True:
        frame = camera.process_frame()
        if frame is None:
            break
        
        if not frame_queue.empty():
            try:
                frame_queue.get_nowait()
            except queue.Empty:
                pass
        frame_queue.put(frame)

        # Update elapsed time for recording
        camera.update_elapsed_time()
        
        # If recording, write the frame
        if camera.settings.recording:
            camera.videoOut.write(frame)

@app.on_event("startup")
async def startup_event():
    threading.Thread(target=camera_thread, daemon=True).start()

def gen_frames():
    while True:
        frame = frame_queue.get()
        _, buffer = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

@app.get("/")
async def index():
    return HTMLResponse("""
    <html>
        <head>
            <title>Thermal Camera Stream</title>
            <style>
                .button-container { margin-top: 10px; }
                button { margin-right: 5px; }
            </style>
        </head>
        <body>
            <h1>Thermal Camera Stream</h1>
            <img src="/video_feed" width="640" height="480" />
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
    camera.handle_command(cmd)
    return {"status": "success", "command": cmd}

@app.on_event("shutdown")
async def shutdown_event():
    camera.close()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
