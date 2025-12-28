# File: display_hybrid.py
# Hybrid display - toggles between local pygame and remote web server
# Only one mode active at a time to maximize performance

import os
import sys
import time
import threading
import queue
import signal
import pygame
import cv2
import numpy as np
from thermal_camera import ThermalCamera
from utils import wait_for_device, print_info

DEVICE_PATH = '/dev/video0'
DEVICE_TIMEOUT = 120
TARGET_FPS = 25
WEB_PORT = 8000

# Colors
COLOR_BG = (40, 40, 40)
COLOR_BUTTON = (70, 70, 70)
COLOR_BUTTON_HOVER = (100, 100, 100)
COLOR_BUTTON_ACTIVE = (50, 120, 50)
COLOR_BUTTON_REMOTE = (120, 50, 50)
COLOR_TEXT = (220, 220, 220)


class AppState:
    """Shared application state."""
    def __init__(self):
        self.mode = "local"  # "local" or "remote"
        self.camera = None
        self.running = True
        self.frame_queue = queue.Queue(maxsize=1)
        self.web_server = None
        self.web_thread = None
        self.switch_requested = None  # "local" or "remote"


class Button:
    def __init__(self, rect, label, command, font, color=COLOR_BUTTON):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.command = command
        self.font = font
        self.base_color = color
        self.hovered = False
        self.active = False

    def draw(self, surface):
        if self.active:
            color = COLOR_BUTTON_ACTIVE
        elif self.hovered:
            color = COLOR_BUTTON_HOVER
        else:
            color = self.base_color

        pygame.draw.rect(surface, color, self.rect, border_radius=5)
        pygame.draw.rect(surface, COLOR_TEXT, self.rect, width=1, border_radius=5)

        text = self.font.render(self.label, True, COLOR_TEXT)
        text_rect = text.get_rect(center=self.rect.center)
        surface.blit(text, text_rect)

    def check_hover(self, pos):
        self.hovered = self.rect.collidepoint(pos)

    def check_click(self, pos):
        return self.rect.collidepoint(pos)


def init_camera_with_retry(max_retries=5, retry_delay=3):
    """Initialize camera with retry logic."""
    for attempt in range(max_retries):
        try:
            print(f"Camera init attempt {attempt + 1}/{max_retries}")
            camera = ThermalCamera()
            print("Camera initialized successfully")
            return camera
        except Exception as e:
            print(f"Camera init failed: {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay}s...")
                time.sleep(retry_delay)
    print("Failed to initialize camera after all retries")
    return None


def bgr_to_pygame_surface(bgr_frame):
    """Convert OpenCV BGR frame to pygame surface."""
    rgb_frame = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
    rgb_frame = np.transpose(rgb_frame, (1, 0, 2))
    return pygame.surfarray.make_surface(rgb_frame)


# ============== Web Server (FastAPI) ==============

def create_web_app(state: AppState):
    """Create FastAPI app for remote mode."""
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse

    app = FastAPI()

    def gen_frames():
        """Generate MJPEG frames for streaming."""
        while state.mode == "remote" and state.running:
            try:
                frame = state.frame_queue.get(timeout=1.0)
                _, buffer = cv2.imencode('.jpg', frame)
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error encoding frame: {e}")
                continue

    @app.get("/")
    async def index():
        return HTMLResponse(f"""
        <html>
            <head>
                <title>Thermal Camera - Remote Mode</title>
                <style>
                    body {{
                        margin: 0;
                        padding: 20px;
                        background: #1a1a1a;
                        color: #ddd;
                        font-family: sans-serif;
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                    }}
                    h1 {{ color: #ff6b6b; margin-bottom: 10px; }}
                    .status {{ color: #6bff6b; margin-bottom: 20px; }}
                    .video-container {{
                        border: 2px solid #444;
                        border-radius: 8px;
                        overflow: hidden;
                    }}
                    .controls {{
                        margin-top: 20px;
                        display: flex;
                        gap: 10px;
                        flex-wrap: wrap;
                        justify-content: center;
                    }}
                    button {{
                        padding: 15px 25px;
                        font-size: 16px;
                        border: none;
                        border-radius: 5px;
                        cursor: pointer;
                        background: #444;
                        color: #ddd;
                    }}
                    button:hover {{ background: #555; }}
                    .btn-local {{
                        background: #c9302c;
                        color: white;
                        font-weight: bold;
                    }}
                    .btn-local:hover {{ background: #ac2925; }}
                </style>
            </head>
            <body>
                <h1>Thermal Camera</h1>
                <div class="status">Remote Mode Active</div>
                <div class="video-container">
                    <img src="/video_feed" width="768" height="576" />
                </div>
                <div class="controls">
                    <button onclick="sendCommand('m')">Colormap</button>
                    <button onclick="sendCommand('h')">HUD</button>
                    <button onclick="sendCommand('r')">Record</button>
                    <button onclick="sendCommand('p')">Snapshot</button>
                    <button onclick="sendCommand('f')">Contrast +</button>
                    <button onclick="sendCommand('v')">Contrast -</button>
                    <button class="btn-local" onclick="switchToLocal()">Switch to Local Display</button>
                </div>
                <script>
                    function sendCommand(cmd) {{
                        fetch('/command/' + cmd).then(r => r.json()).then(console.log);
                    }}
                    function switchToLocal() {{
                        if(confirm('Switch display back to Pi screen?')) {{
                            fetch('/switch/local').then(() => {{
                                document.body.innerHTML = '<h1 style="color:#ff6b6b;text-align:center;margin-top:100px;">Switched to Local Mode</h1><p style="text-align:center;color:#888;">The display is now on the Pi screen.</p>';
                            }});
                        }}
                    }}
                </script>
            </body>
        </html>
        """)

    @app.get("/video_feed")
    async def video_feed():
        return StreamingResponse(gen_frames(), media_type="multipart/x-mixed-replace; boundary=frame")

    @app.get("/command/{cmd}")
    async def execute_command(cmd: str):
        if state.camera is None:
            return JSONResponse({"status": "error", "message": "Camera not initialized"})
        state.camera.handle_command(cmd)
        return JSONResponse({"status": "success", "command": cmd})

    @app.get("/switch/local")
    async def switch_to_local():
        state.switch_requested = "local"
        return JSONResponse({"status": "switching", "to": "local"})

    @app.get("/health")
    async def health():
        return JSONResponse({
            "status": "healthy" if state.camera else "degraded",
            "mode": state.mode
        })

    return app


def start_web_server(state: AppState):
    """Start the web server in a background thread."""
    import uvicorn

    app = create_web_app(state)
    config = uvicorn.Config(app, host="0.0.0.0", port=WEB_PORT, log_level="warning")
    state.web_server = uvicorn.Server(config)

    def run():
        state.web_server.run()

    state.web_thread = threading.Thread(target=run, daemon=True)
    state.web_thread.start()
    print(f"Web server started on port {WEB_PORT}")


def stop_web_server(state: AppState):
    """Stop the web server."""
    if state.web_server:
        state.web_server.should_exit = True
        # Give it a moment to shut down
        time.sleep(0.5)
        state.web_server = None
        state.web_thread = None
        print("Web server stopped")


# ============== Main Application ==============

def create_buttons(font, button_x, screen_height, mode):
    """Create control buttons positioned on the right side."""
    button_width = 140
    button_height = 55
    button_spacing = 8

    if mode == "local":
        button_defs = [
            ("Colormap", 'm', COLOR_BUTTON),
            ("HUD", 'h', COLOR_BUTTON),
            ("Record", 'r', COLOR_BUTTON),
            ("Snapshot", 'p', COLOR_BUTTON),
            ("Contrast +", 'f', COLOR_BUTTON),
            ("Contrast -", 'v', COLOR_BUTTON),
            ("Remote", 'remote', COLOR_BUTTON_REMOTE),
        ]
    else:
        button_defs = [
            ("Local", 'local', COLOR_BUTTON_ACTIVE),
        ]

    total_height = len(button_defs) * button_height + (len(button_defs) - 1) * button_spacing
    start_y = (screen_height - total_height) // 2

    buttons = []
    for i, (label, cmd, color) in enumerate(button_defs):
        y = start_y + i * (button_height + button_spacing)
        rect = (button_x, y, button_width, button_height)
        buttons.append(Button(rect, label, cmd, font, color))

    return buttons


def camera_capture_loop(state: AppState):
    """Background thread that captures frames from camera."""
    while state.running:
        if state.camera is None:
            time.sleep(1)
            continue

        try:
            frame = state.camera.process_frame()
            if frame is None:
                print("Camera returned None, reinitializing...")
                time.sleep(2)
                state.camera = init_camera_with_retry(max_retries=3)
                continue

            state.camera.update_elapsed_time()

            if state.camera.settings.recording:
                state.camera.videoOut.write(frame)

            # Update frame queue (drop old frame if full)
            if not state.frame_queue.empty():
                try:
                    state.frame_queue.get_nowait()
                except queue.Empty:
                    pass
            state.frame_queue.put(frame)

        except Exception as e:
            print(f"Error in capture loop: {e}")
            time.sleep(1)


def run_local_mode(state: AppState, screen, clock):
    """Run the local pygame display mode."""
    print("\n=== LOCAL MODE ===\n")

    screen_width, screen_height = screen.get_size()

    # Reserve space for buttons
    button_panel_width = 160
    video_area_width = screen_width - button_panel_width

    # Calculate scaling
    frame_width, frame_height = state.camera.settings.new_dimensions
    scale_x = video_area_width / frame_width
    scale_y = screen_height / frame_height
    scale = min(scale_x, scale_y)

    scaled_width = int(frame_width * scale)
    scaled_height = int(frame_height * scale)
    offset_x = (video_area_width - scaled_width) // 2
    offset_y = (screen_height - scaled_height) // 2

    # Create buttons
    font = pygame.font.Font(None, 24)
    button_x = video_area_width + (button_panel_width - 140) // 2
    buttons = create_buttons(font, button_x, screen_height, "local")

    frame_count = 0
    fps_time = time.time()

    # Ignore early QUIT events (systemd can cause spurious events)
    ignore_quit_until = time.time() + 5.0

    while state.running and state.mode == "local":
        # Check for mode switch request
        if state.switch_requested == "remote":
            state.switch_requested = None
            state.mode = "remote"
            break

        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                # Ignore QUIT events in first 5 seconds (spurious from systemd)
                if time.time() < ignore_quit_until:
                    print(f"Ignoring early QUIT event")
                    continue
                print("Received QUIT event, exiting...")
                state.running = False
            elif event.type == pygame.MOUSEMOTION:
                for button in buttons:
                    button.check_hover(event.pos)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                for button in buttons:
                    if button.check_click(event.pos):
                        if button.command == 'remote':
                            state.mode = "remote"
                        elif button.command in ['m', 'h', 'r', 'p', 'f', 'v']:
                            state.camera.handle_command(button.command)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE or event.key == pygame.K_q:
                    state.running = False
                elif event.key == pygame.K_m:
                    state.camera.handle_command('m')
                elif event.key == pygame.K_h:
                    state.camera.handle_command('h')
                elif event.key == pygame.K_r:
                    state.camera.handle_command('r')
                elif event.key == pygame.K_p:
                    state.camera.handle_command('p')
                elif event.key == pygame.K_f:
                    state.camera.handle_command('f')
                elif event.key == pygame.K_v:
                    state.camera.handle_command('v')

        # Update recording button state
        for button in buttons:
            if button.command == 'r':
                button.active = state.camera.settings.recording

        # Get frame
        try:
            frame = state.frame_queue.get(timeout=0.1)
        except queue.Empty:
            clock.tick(TARGET_FPS)
            continue

        # Convert and scale
        surface = bgr_to_pygame_surface(frame)
        if scale != 1.0:
            surface = pygame.transform.scale(surface, (scaled_width, scaled_height))

        # Draw
        screen.fill(COLOR_BG)
        screen.blit(surface, (offset_x, offset_y))
        for button in buttons:
            button.draw(screen)
        pygame.display.flip()

        # FPS tracking
        frame_count += 1
        if frame_count % 100 == 0:
            elapsed = time.time() - fps_time
            print(f"Local FPS: {100/elapsed:.1f}")
            fps_time = time.time()

        clock.tick(TARGET_FPS)


def run_remote_mode(state: AppState, screen, clock):
    """Run the remote web server mode with minimal local display."""
    print("\n=== REMOTE MODE ===\n")

    # Start web server
    start_web_server(state)

    screen_width, screen_height = screen.get_size()
    font_large = pygame.font.Font(None, 48)
    font_small = pygame.font.Font(None, 28)

    # Create minimal button panel
    button_panel_width = 160
    button_x = screen_width - button_panel_width + 10
    font_btn = pygame.font.Font(None, 24)
    buttons = create_buttons(font_btn, button_x, screen_height, "remote")

    # Get local IP for display (with timeout to avoid hanging without network)
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(2)  # 2 second timeout
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except:
        local_ip = "check ip via: hostname -I"

    while state.running and state.mode == "remote":
        # Check for mode switch request
        if state.switch_requested == "local":
            state.switch_requested = None
            state.mode = "local"
            break

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                state.running = False
            elif event.type == pygame.MOUSEMOTION:
                for button in buttons:
                    button.check_hover(event.pos)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                for button in buttons:
                    if button.check_click(event.pos):
                        if button.command == 'local':
                            state.mode = "local"
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    state.mode = "local"

        # Draw minimal "remote mode" screen
        screen.fill((20, 20, 30))

        # Title
        title = font_large.render("REMOTE MODE", True, (255, 100, 100))
        title_rect = title.get_rect(center=(screen_width//2 - 80, screen_height//3))
        screen.blit(title, title_rect)

        # URL info
        url_text = f"http://{local_ip}:{WEB_PORT}"
        url = font_small.render(url_text, True, (100, 255, 100))
        url_rect = url.get_rect(center=(screen_width//2 - 80, screen_height//2))
        screen.blit(url, url_rect)

        info = font_small.render("View on any browser", True, (150, 150, 150))
        info_rect = info.get_rect(center=(screen_width//2 - 80, screen_height//2 + 40))
        screen.blit(info, info_rect)

        # Draw button
        for button in buttons:
            button.draw(screen)

        pygame.display.flip()
        clock.tick(10)  # Low FPS for idle screen

    # Stop web server when leaving remote mode
    stop_web_server(state)


def main():
    print_info()
    print("\n=== Hybrid Display Mode ===\n")

    # Wait for camera
    print(f"Waiting for camera device {DEVICE_PATH}...")
    if not wait_for_device(DEVICE_PATH, timeout=DEVICE_TIMEOUT):
        print(f"Warning: Device {DEVICE_PATH} not found")

    time.sleep(2)

    # Initialize state
    state = AppState()
    state.camera = init_camera_with_retry()
    if state.camera is None:
        print("ERROR: Could not initialize camera")
        sys.exit(1)

    # Start camera capture thread
    capture_thread = threading.Thread(target=camera_capture_loop, args=(state,), daemon=True)
    capture_thread.start()

    # Initialize pygame
    pygame.init()
    pygame.mouse.set_visible(True)

    display_info = pygame.display.Info()
    screen_width = display_info.current_w
    screen_height = display_info.current_h
    print(f"Screen: {screen_width}x{screen_height}")

    screen = pygame.display.set_mode((screen_width, screen_height), pygame.FULLSCREEN)
    pygame.display.set_caption("Thermal Camera")
    clock = pygame.time.Clock()

    print("\nStarting in LOCAL mode...")
    print("Press 'Remote' button to switch to web server mode\n")

    # Main loop - switch between modes
    while state.running:
        if state.mode == "local":
            run_local_mode(state, screen, clock)
        elif state.mode == "remote":
            run_remote_mode(state, screen, clock)

    # Cleanup
    print("\nShutting down...")
    state.running = False
    stop_web_server(state)
    if state.camera:
        state.camera.close()
    pygame.quit()
    print("Done")


if __name__ == "__main__":
    main()
