"""The built-in procedurally drawn cat. Colour, mood tint and accessories are customizable."""
import math

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QPainter, QPen, QPolygonF

from .view import BASE, View

MOOD_TINT = {
    "sick": (QColor(120, 190, 90), 0.45),
    "hot": (QColor(240, 110, 80), 0.35),
    "hungry": (QColor(190, 180, 160), 0.4),
    "sad": (QColor(120, 150, 200), 0.35),
}


def tinted(color: QColor, mood: str) -> QColor:
    if mood not in MOOD_TINT:
        return QColor(color)
    t, a = MOOD_TINT[mood]
    return QColor(int(color.red() * (1 - a) + t.red() * a),
                  int(color.green() * (1 - a) + t.green() * a),
                  int(color.blue() * (1 - a) + t.blue() * a))


def paint_body(p: QPainter, v: View):
    p.save()
    base = tinted(v.color, v.mood)
    dark = base.darker(130)
    outline = QPen(QColor(60, 40, 30), 2.5)

    p.translate(BASE / 2, BASE)
    p.scale(v.facing, 1)

    sleeping = v.state == "sleep"
    walking = v.state in ("walk", "chase", "scared", "fetch")
    bob = math.sin(v.phase) * (3 if walking else 1.5)
    squash = 0.85 if sleeping else 1.0

    # Tail
    wag = math.sin(v.phase * (2.5 if v.mood == "happy" else 1)) * 14
    p.setPen(QPen(dark, 7, cap=Qt.PenCapStyle.RoundCap))
    droop = 10 if v.mood == "sad" else 0
    p.drawLine(QPointF(-30, -34), QPointF(-48, -52 + wag * 0.3 - (0 if sleeping else 8) + droop))

    # Legs
    p.setPen(QPen(dark, 8, cap=Qt.PenCapStyle.RoundCap))
    for i, lx in enumerate((-18, -6, 10, 22)):
        swing = math.sin(v.phase + i * math.pi / 2) * 8 if walking else 0
        lift = max(0, math.sin(v.phase + i * math.pi / 2)) * 5 if walking else 0
        p.drawLine(QPointF(lx, -18), QPointF(lx + swing, -2 - lift))

    # Body
    p.setPen(outline)
    p.setBrush(QBrush(base))
    p.drawEllipse(QRectF(-36, -58 * squash + bob * 0.5, 72, 42 * squash + 6))

    # Head and ears
    eating = v.state == "eat"
    head_c = QPointF(26, -58 * squash + bob + (8 if sleeping else 0) + (10 if eating else 0))
    for sx in (-1, 1):
        p.drawPolygon(QPolygonF([QPointF(head_c.x() + sx * 6, head_c.y() - 14),
                                 QPointF(head_c.x() + sx * 18, head_c.y() - 30),
                                 QPointF(head_c.x() + sx * 21, head_c.y() - 8)]))
    p.drawEllipse(head_c, 24, 20)

    _draw_eyes(p, v, head_c, sleeping or eating)

    p.setBrush(QBrush(QColor(220, 110, 120)))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(QPointF(head_c.x() + 12, head_c.y() + 4), 3, 2.2)

    _draw_accessory(p, v.accessory, head_c)
    p.restore()


def _draw_eyes(p: QPainter, v: View, head_c: QPointF, closed: bool):
    p.setPen(QPen(QColor(40, 30, 25), 2.2))
    if closed or (v.state == "idle" and int(v.now * 2) % 11 == 0):
        for ex in (head_c.x() - 2, head_c.x() + 14):
            p.drawArc(QRectF(ex - 5, head_c.y() - 6, 10, 8), 200 * 16, 140 * 16)
        return
    dx = (v.cursor.x() - BASE / 2) * v.facing - head_c.x()
    dy = v.cursor.y() - (BASE + head_c.y())
    d = math.hypot(dx, dy) or 1.0
    ox, oy = dx / d * 2.5, dy / d * 2.5
    wide = 6.5 if v.state in ("scared", "alert") else 5.0
    for ex in (head_c.x() - 2, head_c.x() + 14):
        p.setBrush(QBrush(QColor(255, 255, 255)))
        p.drawEllipse(QPointF(ex, head_c.y() - 3), wide, wide + 1)
        p.setBrush(QBrush(QColor(30, 25, 25)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(ex + ox, head_c.y() - 3 + oy), 2.6, 3.2)
        p.setPen(QPen(QColor(40, 30, 25), 2.2))


def _draw_accessory(p: QPainter, kind: str, head_c: QPointF):
    hx, hy = head_c.x(), head_c.y()
    p.setPen(QPen(QColor(60, 40, 30), 2))
    if kind == "bow":
        p.setBrush(QBrush(QColor(235, 90, 140)))
        bx, by = hx - 14, hy - 14
        p.drawPolygon(QPolygonF([QPointF(bx, by), QPointF(bx - 11, by - 7), QPointF(bx - 11, by + 7)]))
        p.drawPolygon(QPolygonF([QPointF(bx, by), QPointF(bx + 11, by - 7), QPointF(bx + 11, by + 7)]))
        p.drawEllipse(QPointF(bx, by), 3.5, 3.5)
    elif kind == "hat":
        p.setBrush(QBrush(QColor(120, 90, 220)))
        p.drawPolygon(QPolygonF([QPointF(hx - 11, hy - 16), QPointF(hx + 11, hy - 16), QPointF(hx, hy - 44)]))
        p.setBrush(QBrush(QColor(250, 220, 90)))
        p.drawEllipse(QPointF(hx, hy - 44), 4, 4)
    elif kind == "glasses":
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(30, 30, 30), 2.2))
        for ex in (hx - 2, hx + 14):
            p.drawEllipse(QPointF(ex, hy - 3), 8, 8)
        p.drawLine(QPointF(hx + 6, hy - 3), QPointF(hx + 6, hy - 3))
        p.drawLine(QPointF(hx + 5, hy - 5), QPointF(hx + 7, hy - 5))


def paint_overlays(p: QPainter, v: View):
    """Mood and state decorations (zzz, hearts, sweat...), drawn on top of any renderer."""
    p.save()
    p.setPen(QColor(60, 60, 60))
    font = p.font()
    font.setBold(True)
    font.setPointSize(12)
    p.setFont(font)
    mid = BASE / 2
    if v.state == "sleep":
        for i in range(3):
            off = (v.now * 20 + i * 12) % 36
            p.drawText(QPointF(mid + 20 + i * 6, 52 - off), "z")
    elif v.state == "scared":
        p.setPen(QColor(200, 40, 40))
        p.drawText(QPointF(mid + 4, 24), "!")
    elif v.state == "alert":
        big = p.font()
        big.setPointSize(int(18 + 3 * math.sin(v.now * 12)))
        p.setFont(big)
        p.setPen(QColor(235, 140, 20))
        p.drawText(QPointF(mid + 2, 26), "!")
        p.drawText(QPointF(mid + 22, 36), "!")
    if v.hearts:
        p.setPen(QColor(230, 60, 100))
        for i in range(3):
            off = (v.now * 40 + i * 14) % 40
            p.drawText(QPointF(mid - 10 + i * 12, 40 - off * 0.6), "♥")
    if v.mood == "hot":
        p.setBrush(QColor(110, 190, 240))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(mid + 30, 28 + (math.sin(v.now * 6) + 1) * 3), 3, 4.5)
    elif v.mood == "sick":
        p.setPen(QColor(90, 140, 60))
        p.drawText(QPointF(mid + 28, 24), "~")
    elif v.mood == "hungry":
        p.setPen(QColor(120, 80, 40))
        p.drawText(QPointF(mid + 26, 24), "?")
    elif v.mood == "sad":
        p.setPen(QColor(90, 120, 190))
        p.drawText(QPointF(mid + 26, 24), "...")
    p.restore()


class DrawnRenderer:
    name = "Drawn (customizable)"

    def paint(self, p: QPainter, v: View):
        paint_body(p, v)
        paint_overlays(p, v)
