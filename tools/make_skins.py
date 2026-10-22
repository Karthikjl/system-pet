"""Generate the sample sprite skins in ./skins (run: python3 tools/make_skins.py).

Use it as a template: a skin is a folder with skin.json and PNG frames drawn facing right,
feet at the bottom edge. Only the "idle" state is required.
"""
import json
import math
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QGuiApplication, QImage, QPainter, QPainterPath, QPen

from system_pet.render.drawn import paint_body
from system_pet.render.view import BASE, View

SCALE = 2
OUT = Path(__file__).resolve().parents[1] / "skins"


def canvas():
    img = QImage(BASE * SCALE, BASE * SCALE, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.scale(SCALE, SCALE)
    return img, p


def ghost(p, state, t):
    bob = math.sin(t * 2 * math.pi) * (4 if state == "walk" else 2)
    p.setPen(QPen(QColor(90, 100, 130), 2.5))
    p.setBrush(QBrush(QColor(235, 240, 255)))
    path = QPainterPath()
    top, bottom = 22 + bob, 108 + bob
    path.moveTo(28, bottom)
    path.lineTo(28, top + 34)
    path.arcTo(QRectF(28, top, 64, 68), 180, -180)
    path.lineTo(92, bottom)
    for i in range(4):                      # scalloped hem
        x1 = 92 - i * 16
        path.quadTo(x1 - 8, bottom - 14 if i % 2 == 0 else bottom + 6, x1 - 16, bottom)
    path.closeSubpath()
    p.drawPath(path)
    p.setBrush(QBrush(QColor(40, 40, 60)))
    p.setPen(Qt.PenStyle.NoPen)
    if state == "sleep":
        p.setPen(QPen(QColor(40, 40, 60), 2.5))
        for ex in (50, 72):
            p.drawArc(QRectF(ex - 5, top + 36, 10, 8), 200 * 16, 140 * 16)
    else:
        r = 6.5 if state == "scared" else 4.5
        for ex in (50, 72):
            p.drawEllipse(QPointF(ex, top + 40), r * 0.8, r * 1.2)
        if state == "scared":
            p.drawEllipse(QPointF(61, top + 56), 5, 7)


def write_skin(name, title, fps, states):
    folder = OUT / name
    folder.mkdir(parents=True, exist_ok=True)
    frames = {}
    for state, n, draw in states:
        files = []
        for i in range(n):
            img, p = canvas()
            draw(p, state, i / n)
            p.end()
            fn = f"{state}_{i}.png"
            img.save(str(folder / fn))
            files.append(fn)
        frames[state] = files
    (folder / "skin.json").write_text(json.dumps(
        {"name": title, "author": "System Pet", "license": "MIT", "fps": fps, "frames": frames}, indent=2))


def blue_cat(p, state, t):
    v = View(state=state, phase=t * 2 * math.pi, now=t, color=QColor("#7fb2f0"), accessory="bow",
             cursor=QPointF(BASE, BASE / 2))
    paint_body(p, v)


if __name__ == "__main__":
    app = QGuiApplication(sys.argv)
    common = [("idle", 2), ("walk", 4), ("sleep", 1), ("scared", 1), ("drag", 1), ("fall", 1)]
    write_skin("blue-cat", "Blue Cat", 8, [(s, n, blue_cat) for s, n in common])
    write_skin("ghost", "Ghost", 6, [(s, n, ghost) for s, n in common])
    print("skins written to", OUT)
