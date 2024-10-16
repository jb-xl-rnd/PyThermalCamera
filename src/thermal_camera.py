# File: thermal_camera.py

import cv2
import numpy as np
import time
from settings import CameraSettings
from utils import (
    is_raspberrypi, calculate_temperature, find_extreme_temperature, 
    calculate_average_temperature, draw_text, COLORMAPS
)

class ThermalCamera:
    def __init__(self, device=0):
        self.isPi = is_raspberrypi()  # Set this before initializing the camera
        self.cap = self.init_camera(device)
        self.settings = CameraSettings()
        self.setup_key_handlers()
        self.heatmap = None

    def init_camera(self, device):
        cap = cv2.VideoCapture(f'/dev/video{device}', cv2.CAP_V4L)
        cap.set(cv2.CAP_PROP_CONVERT_RGB, 0.0 if self.isPi else False)
        return cap

    def setup_key_handlers(self):
        self.key_handlers = {
            'm': self.cycle_colormap,
            'h': lambda: self.update_setting('hud', not self.settings.hud),
            'r': self.toggle_recording,
            'p': self.take_snapshot,
            'f': lambda: self.update_setting('alpha', min(3.0, self.settings.alpha + 0.1)),
            'v': lambda: self.update_setting('alpha', max(0.1, self.settings.alpha - 0.1))
        }

    def update_setting(self, attr: str, value) -> None:
        setattr(self.settings, attr, value)
        print(f"Updated {attr} to {value}")  # For debugging

    def toggle_recording(self):
        if self.settings.recording:
            self.stop_recording()
        else:
            self.start_recording()

    def take_snapshot(self):
        self.settings.snaptime = self.snapshot()

    def process_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            return None

        imdata, thdata = np.array_split(frame, 2)
        temp = calculate_temperature(thdata[96][128])
        maxtemp, maxpos = find_extreme_temperature(thdata, np.argmax, self.settings.width)
        mintemp, minpos = find_extreme_temperature(thdata, np.argmin, self.settings.width)
        avgtemp = calculate_average_temperature(thdata)
        
        self.heatmap = self.create_heatmap(imdata)
        self.draw_overlay(self.heatmap, temp, maxtemp, maxpos, mintemp, minpos, avgtemp)
        
        return self.heatmap

    def create_heatmap(self, imdata):
        bgr = cv2.cvtColor(imdata, cv2.COLOR_YUV2BGR_YUYV)
        bgr = cv2.convertScaleAbs(bgr, alpha=self.settings.alpha, beta=0)
        bgr = cv2.resize(bgr, self.settings.new_dimensions, interpolation=cv2.INTER_CUBIC)
        if self.settings.rad > 0:
            bgr = cv2.blur(bgr, (self.settings.rad, self.settings.rad))
        
        cmap, self.settings.cmapText = COLORMAPS[self.settings.colormap]
        heatmap = cv2.applyColorMap(bgr, cmap)
        
        if self.settings.cmapText == 'Inv Rainbow':
            heatmap = cv2.cvtColor(heatmap, cv2.COLOR_BGR2RGB)
        
        return heatmap

    def draw_overlay(self, heatmap, temp, maxtemp, maxpos, mintemp, minpos, avgtemp):
        center = tuple(d // 2 for d in self.settings.new_dimensions)
        for offset in [(0, 20), (20, 0)]:
            cv2.line(heatmap, 
                     (center[0] - offset[0], center[1] - offset[1]),
                     (center[0] + offset[0], center[1] + offset[1]),
                     (255,255,255), 2)
            cv2.line(heatmap, 
                     (center[0] - offset[0], center[1] - offset[1]),
                     (center[0] + offset[0], center[1] + offset[1]),
                     (0,0,0), 1)
        
        draw_text(heatmap, f"{temp} C", (center[0] + 10, center[1] - 10))

        if self.settings.hud:
            self.draw_hud(heatmap, avgtemp)

        if maxtemp > avgtemp + self.settings.threshold:
            self.draw_temp_point(heatmap, maxpos, maxtemp, (0,0,255))

        if mintemp < avgtemp - self.settings.threshold:
            self.draw_temp_point(heatmap, minpos, mintemp, (255,0,0))

    def draw_hud(self, heatmap, avgtemp):
        cv2.rectangle(heatmap, (0, 0), (160, 120), (0,0,0), -1)
        hud_items = [
            ('Avg Temp', f'{avgtemp} C'),
            ('Label Threshold', f'{self.settings.threshold} C'),
            ('Colormap', self.settings.cmapText),
            ('Blur', str(self.settings.rad)),
            ('Scaling', str(self.settings.scale)),
            ('Contrast', str(self.settings.alpha)),
            ('Snapshot', self.settings.snaptime),
            ('Recording', self.settings.elapsed)
        ]
        for i, (label, value) in enumerate(hud_items):
            color = (40, 40, 255) if label == 'Recording' and self.settings.recording else (0, 255, 255)
            draw_text(heatmap, f'{label}: {value}', (10, 14 + i*14), font_scale=0.4, color=color)

    def draw_temp_point(self, heatmap, pos, temp, color):
        x, y = (p * self.settings.scale for p in pos)
        cv2.circle(heatmap, (x, y), 5, (0,0,0), 2)
        cv2.circle(heatmap, (x, y), 5, color, -1)
        draw_text(heatmap, f"{temp} C", (x+10, y+5))

    def cycle_colormap(self):
        self.settings.colormap = (self.settings.colormap + 1) % len(COLORMAPS)
        self.settings.cmapText = COLORMAPS[self.settings.colormap][1]

    def start_recording(self):
        if not self.settings.recording:
            self.videoOut = cv2.VideoWriter(
                time.strftime("%Y%m%d--%H%M%S") + 'output.avi',
                cv2.VideoWriter_fourcc(*'XVID'),
                25,
                self.settings.new_dimensions
            )
            self.settings.recording = True
            self.start_time = time.time()

    def stop_recording(self):
        if self.settings.recording:
            self.videoOut.release()
            self.settings.recording = False
            self.settings.elapsed = "00:00:00"

    def snapshot(self):
        cv2.imwrite(f"TC001{time.strftime('%Y%m%d-%H%M%S')}.png", self.heatmap)
        return time.strftime("%H:%M:%S")

    def handle_command(self, command):
        if command in self.key_handlers:
            self.key_handlers[command]()
        self.update_elapsed_time()

    def update_elapsed_time(self):
        if self.settings.recording:
            self.settings.elapsed = time.strftime("%H:%M:%S", time.gmtime(time.time() - self.start_time))

    def close(self):
        self.cap.release()
        if self.settings.recording:
            self.videoOut.release()