"""A big, hard-to-miss reminder card that slides in from the top-right corner."""
import math

from PyQt6.QtCore import (QEasingCurve, QParallelAnimationGroup, QPoint, QPointF, QPropertyAnimation,
                          QRect, QRectF, Qt, QTimer)
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen, QPolygonF
from PyQt6.QtWidgets import QApplication, QWidget

# kind -> (title, accent colour)
KINDS = {
    "water": ("Drink some water", QColor("#3b9be8")),
    "eye": ("Rest your eyes", QColor("#32a866")),
    "pomo_break": ("Break time", QColor("#e8743b")),
    "pomo_work": ("Back to focus", QColor("#8a5be8")),
    "info": ("System Pet", QColor("#e8a23b")),
}
W, H, MARGIN = 380, 104, 22


class Toast(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedSize(W, H)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.kind = "info"
        self.text = ""
        self._group = None
        self._life = QTimer(self)
        self._life.setSingleShot(True)
        self._life.timeout.connect(self.dismiss)
        self._pulse = QTimer(self)
        self._pulse.timeout.connect(self.update)

    # ----- show / hide -----
    def show_message(self, kind: str, text: str, ms: int = 14000):
        self.kind = kind if kind in KINDS else "info"
        self.text = text
        area = QApplication.primaryScreen().availableGeometry()
        end = QPoint(area.right() - W - MARGIN, area.top() + MARGIN)
        start = QPoint(end.x(), area.top() - H)
        self._stop_animation()
        self.setWindowOpacity(0.0)
        self.move(start)
        self.show()
        self.raise_()
        move = QPropertyAnimation(self, b"pos")
        move.setDuration(450)
        move.setStartValue(start)
        move.setEndValue(end)
        move.setEasingCurve(QEasingCurve.Type.OutBack)
        fade = QPropertyAnimation(self, b"windowOpacity")
        fade.setDuration(300)
        fade.setStartValue(0.0)
        fade.setEndValue(1.0)
        self._group = QParallelAnimationGroup(self)
        self._group.addAnimation(move)
        self._group.addAnimation(fade)
        self._group.start()
        self._pulse.start(40)
        self._life.start(ms)

    def dismiss(self):
        self._life.stop()
        if not self.isVisible():
            return
        self._stop_animation()
        fade = QPropertyAnimation(self, b"windowOpacity")
        fade.setDuration(350)
        fade.setStartValue(self.windowOpacity())
        fade.setEndValue(0.0)
        fade.finished.connect(self._hide_now)
        self._group = QParallelAnimationGroup(self)
        self._group.addAnimation(fade)
        self._group.start()

    def _hide_now(self):
        self._pulse.stop()
        self.hide()

    def _stop_animation(self):
        if self._group is not None:
            self._group.stop()
            self._group.deleteLater()
            self._group = None

    def mousePressEvent(self, _):
        self.dismiss()

    # ----- drawing -----
    def paintEvent(self, _):
        title, accent = KINDS[self.kind]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        card = QRectF(4, 4, W - 8, H - 8)

        p.setPen(Qt.PenStyle.NoPen)
        for i, a in enumerate((18, 12, 7)):           # soft shadow
            p.setBrush(QColor(0, 0, 0, a))
            p.drawRoundedRect(card.adjusted(-i, -i + 2, i, i + 3), 16, 16)
        p.setBrush(QColor(255, 255, 255))
        p.setPen(QPen(accent, 2.5))
        p.drawRoundedRect(card, 14, 14)

        # icon disc, gently pulsing
        pulse = 1.0 + 0.06 * math.sin(self._phase() * 6)
        cx, cy, r = 52, H / 2, 27 * pulse
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(accent)
        p.drawEllipse(QPointF(cx, cy), r, r)
        self._draw_glyph(p, cx, cy)

        tx = 96
        font = QFont(self.font())
        font.setBold(True)
        font.setPointSize(13)
        p.setFont(font)
        p.setPen(accent.darker(120))
        p.drawText(QRect(tx, 14, W - tx - 16, 24), int(Qt.AlignmentFlag.AlignVCenter), title)

        font.setBold(False)
        font.setPointSize(10)
        p.setFont(font)
        p.setPen(QColor(55, 55, 65))
        p.drawText(QRect(tx, 40, W - tx - 16, 40),
                   int(Qt.TextFlag.TextWordWrap) | int(Qt.AlignmentFlag.AlignTop), self.text)

        font.setPointSize(8)
        p.setFont(font)
        p.setPen(QColor(150, 150, 160))
        p.drawText(QRect(tx, H - 28, W - tx - 16, 16), int(Qt.AlignmentFlag.AlignRight), "click to dismiss")
        p.end()

    def _phase(self) -> float:
        import time
        return time.monotonic()

    def _draw_glyph(self, p: QPainter, cx: float, cy: float):
        white = QColor(255, 255, 255)
        p.setBrush(white)
        p.setPen(Qt.PenStyle.NoPen)
        if self.kind == "water":                       # droplet
            p.drawPolygon(QPolygonF([QPointF(cx, cy - 15), QPointF(cx - 9, cy + 2), QPointF(cx + 9, cy + 2)]))
            p.drawEllipse(QPointF(cx, cy + 4), 9.5, 9.5)
        elif self.kind == "eye":                       # eye
            p.drawEllipse(QPointF(cx, cy), 15, 9)
            p.setBrush(self._accent())
            p.drawEllipse(QPointF(cx, cy), 5.5, 5.5)
            p.setBrush(white)
            p.drawEllipse(QPointF(cx - 1.8, cy - 1.8), 1.8, 1.8)
        elif self.kind in ("pomo_break", "pomo_work"):  # clock
            p.drawEllipse(QPointF(cx, cy), 14, 14)
            p.setPen(QPen(self._accent(), 2.6, cap=Qt.PenCapStyle.RoundCap))
            p.drawLine(QPointF(cx, cy), QPointF(cx, cy - 9))
            p.drawLine(QPointF(cx, cy), QPointF(cx + 7, cy + 3))
        else:                                          # bell-ish "!"
            f = QFont(self.font())
            f.setBold(True)
            f.setPointSize(24)
            p.setFont(f)
            p.setPen(white)
            p.drawText(QRectF(cx - 20, cy - 22, 40, 44), int(Qt.AlignmentFlag.AlignCenter), "!")

    def _accent(self) -> QColor:
        return KINDS[self.kind][1]
