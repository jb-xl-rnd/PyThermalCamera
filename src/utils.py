# File: utils.py

import io
import cv2
import numpy as np
import time

COLORMAPS = [
    (cv2.COLORMAP_JET, 'Jet'),
    (cv2.COLORMAP_HOT, 'Hot'),
    (cv2.COLORMAP_MAGMA, 'Magma'),
    (cv2.COLORMAP_INFERNO, 'Inferno'),
    (cv2.COLORMAP_PLASMA, 'Plasma'),
    (cv2.COLORMAP_BONE, 'Bone'),
    (cv2.COLORMAP_SPRING, 'Spring'),
    (cv2.COLORMAP_AUTUMN, 'Autumn'),
    (cv2.COLORMAP_VIRIDIS, 'Viridis'),
    (cv2.COLORMAP_PARULA, 'Parula'),
    (cv2.COLORMAP_RAINBOW, 'Inv Rainbow')
]

def is_raspberrypi():
    try:
        with io.open('/sys/firmware/devicetree/base/model', 'r') as m:
            return 'raspberry pi' in m.read().lower()
    except Exception:
        return False

def calculate_temperature(pixel):
    return round((pixel[0] + pixel[1] * 256) / 64 - 273.15, 2)

def find_extreme_temperature(thdata, func, width):
    pos = func(thdata[...,1])
    col, row = divmod(pos, width)
    temp = calculate_temperature(thdata[col][row])
    return temp, (row, col)

def calculate_average_temperature(thdata):
    return round((thdata[...,0].mean() + thdata[...,1].mean() * 256) / 64 - 273.15, 2)

def draw_text(img, text, pos, font=cv2.FONT_HERSHEY_SIMPLEX, font_scale=0.45, color=(0,255,255), thickness=1):
    cv2.putText(img, text, pos, font, font_scale, (0,0,0), thickness+1, cv2.LINE_AA)
    cv2.putText(img, text, pos, font, font_scale, color, thickness, cv2.LINE_AA)

def print_info():
    info = [
        'Les Wright 21 June 2023',
        'https://youtube.com/leslaboratory',
        'A Python program to read, parse and display thermal data from the Topdon TC001 Thermal camera!',
        '',
        'Tested on Debian all features are working correctly',
        'This will work on the Pi However a number of workarounds are implemented!',
        'Seemingly there are bugs in the compiled version of cv2 that ships with the Pi!',
        '',
        'Key Bindings:',
        '',
        'a z: Increase/Decrease Blur',
        's x: Floating High and Low Temp Label Threshold',
        'd c: Change Interpolated scale Note: This will not change the window size on the Pi',
        'f v: Contrast',
        'q w: Fullscreen Windowed (note going back to windowed does not seem to work on the Pi!)',
        'r t: Record and Stop',
        'p : Snapshot',
        'm : Cycle through ColorMaps',
        'h : Toggle HUD'
    ]
    print('\n'.join(info))