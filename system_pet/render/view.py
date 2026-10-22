"""What a renderer needs to know to draw one frame. All coordinates are in a 120x120 box."""
from dataclasses import dataclass, field

from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QColor

BASE = 120


@dataclass
class View:
    state: str = "idle"       # idle walk chase fetch sleep scared drag fall eat
    mood: str = "happy"       # happy sick hot hungry sad
    facing: int = 1
    phase: float = 0.0
    now: float = 0.0
    hearts: bool = False
    cursor: QPointF = field(default_factory=lambda: QPointF(BASE, BASE / 2))
    color: QColor = field(default_factory=lambda: QColor("#f5be6e"))
    accessory: str = "none"
