# File: settings.py

from dataclasses import dataclass
from typing import Tuple

@dataclass
class CameraSettings:
    width: int = 256
    height: int = 192
    scale: int = 3
    alpha: float = 1.0
    colormap: int = 0
    rad: int = 0
    threshold: int = 2
    hud: bool = True
    recording: bool = False
    elapsed: str = "00:00:00"
    snaptime: str = "None"
    dispFullscreen: bool = False
    cmapText: str = 'Jet'

    @property
    def new_dimensions(self) -> Tuple[int, int]:
        return self.width * self.scale, self.height * self.scale
