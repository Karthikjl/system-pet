"""Render the app icon (assets/icon.png and assets/icon.ico) from the drawn cat."""
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PyQt6.QtGui import QColor, QGuiApplication, QImage, QPainter
from PyQt6.QtCore import Qt

from system_pet.render.drawn import DrawnRenderer
from system_pet.render.view import BASE, View

OUT = Path(__file__).resolve().parents[1] / "assets"


def render(px: int) -> QImage:
    img = QImage(px, px, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.scale(px / BASE, px / BASE)
    DrawnRenderer().paint(p, View(color=QColor("#f5be6e"), accessory="bow"))
    p.end()
    return img


if __name__ == "__main__":
    QGuiApplication(sys.argv)
    OUT.mkdir(exist_ok=True)
    print("png:", render(256).save(str(OUT / "icon.png")))
    print("ico:", render(256).save(str(OUT / "icon.ico")))
