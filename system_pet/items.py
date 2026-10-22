"""Little objects the pet can interact with: food to eat and a ball to chase."""
import time

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QPainter, QPen, QPolygonF
from PyQt6.QtWidgets import QWidget

ITEM_SIZE = 30
GRAVITY = 1800.0


class Item(QWidget):
    def __init__(self, kind: str):
        super().__init__()
        self.kind = kind            # "food" | "ball"
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowTransparentForInput)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedSize(ITEM_SIZE, ITEM_SIZE)
        self.x = self.y = 0.0       # bottom-center
        self.vx = self.vy = 0.0
        self.on_ground = False
        self.born = time.monotonic()

    @property
    def age(self) -> float:
        return time.monotonic() - self.born

    def step(self, dt: float, bounds):
        self.vy += GRAVITY * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        left, right = bounds.left() + ITEM_SIZE / 2, bounds.right() - ITEM_SIZE / 2
        if self.x < left:
            self.x, self.vx = left, abs(self.vx) * 0.7
        elif self.x > right:
            self.x, self.vx = right, -abs(self.vx) * 0.7
        ground = bounds.bottom()
        self.on_ground = False
        if self.y >= ground:
            self.y = float(ground)
            if self.kind == "ball" and self.vy > 250:
                self.vy *= -0.55
            else:
                self.vy = 0.0
                self.on_ground = True
            self.vx *= 0.96 if self.kind == "ball" else 0.8
        self.move(int(self.x - ITEM_SIZE / 2), int(self.y - ITEM_SIZE))

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor(60, 40, 30), 2))
        if self.kind == "ball":
            p.setBrush(QBrush(QColor(230, 70, 70)))
            p.drawEllipse(QRectF(3, 3, 24, 24))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(QColor(255, 255, 255, 150)))
            p.drawEllipse(QRectF(8, 8, 7, 5))
        else:   # a fish
            p.setBrush(QBrush(QColor(110, 170, 230)))
            p.drawEllipse(QRectF(3, 9, 20, 13))
            p.drawPolygon(QPolygonF([QPointF(22, 15.5), QPointF(28, 9), QPointF(28, 22)]))
            p.setBrush(QBrush(QColor(30, 30, 30)))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(8, 14), 1.6, 1.6)
        p.end()
