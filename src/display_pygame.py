# File: display_pygame.py
# Direct pygame display - bypasses browser for lower CPU usage

import os
import sys
import time
import pygame
import cv2
import numpy as np
from thermal_camera import ThermalCamera
from utils import wait_for_device, print_info

DEVICE_PATH = '/dev/video0'
DEVICE_TIMEOUT = 120
TARGET_FPS = 25

# Button colors
COLOR_BG = (40, 40, 40)
COLOR_BUTTON = (70, 70, 70)
COLOR_BUTTON_HOVER = (100, 100, 100)
COLOR_BUTTON_ACTIVE = (50, 120, 50)
COLOR_TEXT = (220, 220, 220)
COLOR_RECORDING = (200, 50, 50)


class Button:
    def __init__(self, rect, label, command, font):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.command = command
        self.font = font
        self.hovered = False
        self.active = False

    def draw(self, surface):
        if self.active:
            color = COLOR_BUTTON_ACTIVE
        elif self.hovered:
            color = COLOR_BUTTON_HOVER
        else:
            color = COLOR_BUTTON

        pygame.draw.rect(surface, color, self.rect, border_radius=5)
        pygame.draw.rect(surface, COLOR_TEXT, self.rect, width=1, border_radius=5)

        text = self.font.render(self.label, True, COLOR_TEXT)
        text_rect = text.get_rect(center=self.rect.center)
        surface.blit(text, text_rect)

    def handle_event(self, event, camera):
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                camera.handle_command(self.command)
                return True
        return False


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
    # OpenCV uses BGR, pygame uses RGB
    rgb_frame = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
    # Transpose for pygame (it expects width, height, channels in different order)
    rgb_frame = np.transpose(rgb_frame, (1, 0, 2))
    return pygame.surfarray.make_surface(rgb_frame)


def create_buttons(font, button_x, screen_height):
    """Create control buttons positioned on the right side."""
    button_width = 140
    button_height = 60
    button_spacing = 10

    # Calculate vertical centering for 6 buttons
    total_height = 6 * button_height + 5 * button_spacing
    start_y = (screen_height - total_height) // 2

    button_defs = [
        ("Colormap", 'm'),
        ("HUD", 'h'),
        ("Record", 'r'),
        ("Snapshot", 'p'),
        ("Contrast +", 'f'),
        ("Contrast -", 'v'),
    ]

    buttons = []
    for i, (label, cmd) in enumerate(button_defs):
        y = start_y + i * (button_height + button_spacing)
        rect = (button_x, y, button_width, button_height)
        buttons.append(Button(rect, label, cmd, font))

    return buttons


def main():
    print_info()
    print("\n=== Pygame Direct Display Mode ===\n")

    # Wait for camera device
    print(f"Waiting for camera device {DEVICE_PATH}...")
    if not wait_for_device(DEVICE_PATH, timeout=DEVICE_TIMEOUT):
        print(f"Warning: Device {DEVICE_PATH} not found after {DEVICE_TIMEOUT}s")

    time.sleep(2)  # Let device stabilize

    # Initialize camera
    camera = init_camera_with_retry()
    if camera is None:
        print("ERROR: Could not initialize camera")
        sys.exit(1)

    # Initialize pygame
    pygame.init()
    pygame.mouse.set_visible(True)  # Show mouse for button interaction

    # Get display info for fullscreen
    display_info = pygame.display.Info()
    screen_width = display_info.current_w
    screen_height = display_info.current_h
    print(f"Screen resolution: {screen_width}x{screen_height}")

    # Create fullscreen display
    screen = pygame.display.set_mode((screen_width, screen_height), pygame.FULLSCREEN)
    pygame.display.set_caption("Thermal Camera")

    # Reserve space for buttons on the right (160px panel)
    button_panel_width = 160
    video_area_width = screen_width - button_panel_width

    # Calculate scaling to fit video in remaining space
    frame_width, frame_height = camera.settings.new_dimensions
    scale_x = video_area_width / frame_width
    scale_y = screen_height / frame_height
    scale = min(scale_x, scale_y)

    scaled_width = int(frame_width * scale)
    scaled_height = int(frame_height * scale)

    # Position video on the left, centered vertically
    offset_x = (video_area_width - scaled_width) // 2
    offset_y = (screen_height - scaled_height) // 2

    print(f"Frame size: {frame_width}x{frame_height}")
    print(f"Scaled to: {scaled_width}x{scaled_height}")
    print(f"Video offset: ({offset_x}, {offset_y})")
    print(f"Button panel: {button_panel_width}px on right")

    # Create font and buttons
    font = pygame.font.Font(None, 24)
    button_x = video_area_width + (button_panel_width - 140) // 2  # Center buttons in panel
    buttons = create_buttons(font, button_x, screen_height)

    clock = pygame.time.Clock()
    running = True

    print("\nKey bindings:")
    print("  m: Cycle colormap")
    print("  h: Toggle HUD")
    print("  r: Start/stop recording")
    print("  p: Take snapshot")
    print("  f: Contrast +")
    print("  v: Contrast -")
    print("  q/ESC: Quit")
    print("\nStarting display loop...\n")

    frame_count = 0
    fps_time = time.time()

    while running:
        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE or event.key == pygame.K_q:
                    running = False
                elif event.key == pygame.K_m:
                    camera.handle_command('m')
                elif event.key == pygame.K_h:
                    camera.handle_command('h')
                elif event.key == pygame.K_r:
                    camera.handle_command('r')
                elif event.key == pygame.K_p:
                    camera.handle_command('p')
                elif event.key == pygame.K_f:
                    camera.handle_command('f')
                elif event.key == pygame.K_v:
                    camera.handle_command('v')

            # Handle button events
            for button in buttons:
                button.handle_event(event, camera)

        # Update recording button state
        for button in buttons:
            if button.command == 'r':
                button.active = camera.settings.recording

        # Get frame from camera
        frame = camera.process_frame()
        if frame is None:
            print("Camera returned None frame, reinitializing...")
            time.sleep(2)
            camera = init_camera_with_retry(max_retries=3)
            if camera is None:
                print("Failed to reinitialize camera")
                break
            continue

        camera.update_elapsed_time()

        # Handle recording
        if camera.settings.recording:
            camera.videoOut.write(frame)

        # Convert to pygame surface
        surface = bgr_to_pygame_surface(frame)

        # Scale if needed
        if scale != 1.0:
            surface = pygame.transform.scale(surface, (scaled_width, scaled_height))

        # Clear screen with dark background
        screen.fill(COLOR_BG)

        # Draw video
        screen.blit(surface, (offset_x, offset_y))

        # Draw buttons
        for button in buttons:
            button.draw(screen)

        pygame.display.flip()

        # FPS tracking
        frame_count += 1
        if frame_count % 100 == 0:
            elapsed = time.time() - fps_time
            fps = 100 / elapsed
            print(f"FPS: {fps:.1f}")
            fps_time = time.time()

        # Cap frame rate
        clock.tick(TARGET_FPS)

    # Cleanup
    print("\nShutting down...")
    camera.close()
    pygame.quit()
    print("Done")


if __name__ == "__main__":
    main()
