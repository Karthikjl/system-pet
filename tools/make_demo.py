"""Generate docs/demo.gif and the README screenshots from the real widgets (offscreen, no recorder).

    pip install -r requirements-dev.txt
    python tools/make_demo.py
"""
import math
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
_scratch = tempfile.mkdtemp(prefix="system-pet-demo-")     # never touch the user's real settings
os.environ.update(QT_QPA_PLATFORM="offscreen", SYSTEM_PET_CONFIG_DIR=_scratch + "/cfg",
                  SYSTEM_PET_DATA_DIR=_scratch + "/data")

from PIL import Image
from PyQt6.QtCore import QPointF, QRect, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QImage, QLinearGradient, QPainter, QPen
from PyQt6.QtWidgets import QApplication, QTabWidget

from system_pet.app import Controller
from system_pet.bubble import Bubble
from system_pet.render import discover_skins, make_renderer
from system_pet.render.view import BASE, View
from system_pet.ui.settings_window import SettingsWindow

DOCS = ROOT / "docs"
W, H, GROUND, FPS, PET = 640, 360, 318, 12, 112
MAX_GIF_MB = 2.5


# ---------- scene ----------
def backdrop() -> QImage:
    img = QImage(W, H, QImage.Format.Format_RGB32)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    g = QLinearGradient(0, 0, 0, H)
    g.setColorAt(0, QColor("#4f74cf"))
    g.setColorAt(1, QColor("#b38ae0"))
    p.fillRect(img.rect(), g)
    for x, y, w, h in ((36, 34, 300, 178), (352, 96, 252, 150)):          # fake app windows
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 40))
        p.drawRoundedRect(QRectF(x + 3, y + 5, w, h), 9, 9)
        p.setBrush(QColor(246, 246, 250))
        p.drawRoundedRect(QRectF(x, y, w, h), 9, 9)
        p.setBrush(QColor(222, 224, 234))
        p.drawRoundedRect(QRectF(x, y, w, 26), 9, 9)
        p.drawRect(QRectF(x, y + 16, w, 10))
        for i, c in enumerate(("#ff6159", "#ffbd2e", "#28c940")):
            p.setBrush(QColor(c))
            p.drawEllipse(QPointF(x + 16 + i * 17, y + 13), 5, 5)
        p.setBrush(QColor(205, 208, 222))
        for i in range(4):
            p.drawRoundedRect(QRectF(x + 18, y + 44 + i * 22, w * (0.75 - 0.12 * i), 9), 4, 4)
    p.fillRect(0, GROUND, W, H - GROUND, QColor(18, 18, 28))               # taskbar
    p.setBrush(QColor(255, 255, 255, 60))
    for i in range(5):
        p.drawRoundedRect(QRectF(16 + i * 40, GROUND + 9, 28, 24), 6, 6)
    p.end()
    return img


def draw_pet(img: QImage, renderer, x: float, feet_y: float, view: View):
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.translate(x - PET / 2, feet_y - PET)
    p.scale(PET / BASE, PET / BASE)
    renderer.paint(p, view)
    p.end()


def ease_out_back(t: float) -> float:
    t = max(0.0, min(1.0, t))
    c = 1.70158
    return 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2


def build_frames(ctrl) -> list[Image.Image]:
    s = ctrl.store.s
    renderer = make_renderer(s)
    color = QColor(s.color)
    base = backdrop()

    bubble = Bubble()
    bubble.say("Time for a sip of water!", QRect(0, 0, 10, 10), 600000)
    bubble_pm = bubble.grab()
    bubble.hide()
    ctrl.toast.show_message("water", "Staying hydrated keeps you sharp.", 600000)
    ctrl.toast._stop_animation()
    ctrl.toast.setWindowOpacity(1.0)
    toast_pm = ctrl.toast.grab().scaledToWidth(300, Qt.TransformationMode.SmoothTransformation)
    ctrl.toast.hide()

    total = 10.5
    frames = []
    for i in range(int(total * FPS)):
        t = i / FPS
        img = base.copy()
        feet_y, x, facing, state, hearts = float(GROUND), 330.0, 1, "idle", False
        if t < 2.5:
            state, x = "walk", 90 + 240 * t / 2.5
        elif t < 3.5:
            hearts = True
        elif t < 7.0:
            state = "alert"
            feet_y -= abs(math.sin((t - 3.5) * math.pi / 0.75)) * 38
        elif t < 8.2:
            state, facing, x = "walk", -1, 330 - 100 * (t - 7.0) / 1.2
        else:
            state, facing, x = "sleep", -1, 230.0
        view = View(state=state, mood="happy", facing=facing, phase=t * (10 if state == "walk" else 4),
                    now=t, hearts=hearts, cursor=QPointF(BASE, BASE / 2), color=color,
                    accessory=s.accessory)
        draw_pet(img, renderer, x, feet_y, view)

        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        if state == "alert":
            p.drawPixmap(int(x - bubble_pm.width() / 2), int(GROUND - PET - bubble_pm.height() + 6), bubble_pm)
        if 3.5 <= t < 6.9:
            ty = -toast_pm.height() + (toast_pm.height() + 16) * ease_out_back((t - 3.5) / 0.45)
            p.drawPixmap(W - toast_pm.width() - 14, int(ty), toast_pm)
        p.end()
        frames.append(img)

    def to_pil(q: QImage) -> Image.Image:
        q = q.convertToFormat(QImage.Format.Format_RGB888)
        ptr = q.constBits()
        ptr.setsize(q.sizeInBytes())
        return Image.frombuffer("RGB", (q.width(), q.height()), bytes(ptr), "raw", "RGB", q.bytesPerLine(), 1)

    pil = [to_pil(f) for f in frames]
    palette = pil[int(5.2 * FPS)].quantize(colors=160, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    return [f.quantize(palette=palette, dither=Image.Dither.NONE) for f in pil]


# ---------- screenshots ----------
def save_settings_shots(ctrl):
    win = SettingsWindow(ctrl)
    win.show()
    tabs = win.findChild(QTabWidget)
    for index, name in ((0, "settings-appearance"), (2, "settings-reminders")):
        tabs.setCurrentIndex(index)
        QApplication.processEvents()
        win.grab().save(str(DOCS / f"{name}.png"))
    win.close()


def save_toast_shot(ctrl):
    ctrl.toast.show_message("water", "Time for a sip of water! Staying hydrated keeps you sharp.", 600000)
    ctrl.toast._stop_animation()
    ctrl.toast.setWindowOpacity(1.0)
    ctrl.toast.grab().save(str(DOCS / "toast.png"))
    ctrl.toast.hide()


def save_skin_grid():
    rows = [("Drawn cat", "drawn", "#f5be6e", "none"),
            ("Drawn + hat", "drawn", "#aa88ee", "hat"),
            ("Drawn + glasses", "drawn", "#7fb2f0", "glasses")]
    rows += [(title, key, "#f5be6e", "none") for key, title in discover_skins().items()]
    states = ("idle", "walk", "sleep", "alert")
    cell, label_w, head = 120, 150, 34
    img = QImage(label_w + cell * len(states), head + cell * len(rows), QImage.Format.Format_RGB32)
    img.fill(QColor("#f3f3f6"))
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    font = QFont()
    font.setPointSize(10)
    p.setFont(font)
    for c, state in enumerate(states):
        p.setPen(QColor(90, 90, 100))
        p.drawText(QRect(label_w + c * cell, 0, cell, head), int(Qt.AlignmentFlag.AlignCenter), state)
    for r, (label, key, color, acc) in enumerate(rows):
        y = head + r * cell
        p.setPen(QPen(QColor(220, 220, 228)))
        p.drawLine(0, y, img.width(), y)
        p.setPen(QColor(40, 40, 50))
        p.drawText(QRect(10, y, label_w - 10, cell), int(Qt.AlignmentFlag.AlignVCenter), label)
        renderer = make_renderer(SimpleNamespace(skin=key))
        for c, state in enumerate(states):
            p.save()
            p.translate(label_w + c * cell, y)
            renderer.paint(p, View(state=state, phase=1.0, now=1.0, color=QColor(color), accessory=acc))
            p.restore()
    p.end()
    img.save(str(DOCS / "skins.png"))


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    DOCS.mkdir(exist_ok=True)
    ctrl = Controller()
    for pet in ctrl.pets:
        pet.shutdown()
    ctrl.store.update(name="Mochi", color="#f5be6e", accessory="bow", skin="drawn")

    frames = build_frames(ctrl)
    gif = DOCS / "demo.gif"
    frames[0].save(gif, save_all=True, append_images=frames[1:], duration=int(1000 / FPS), loop=0,
                   optimize=True, disposal=1)
    size = gif.stat().st_size / 1048576
    print(f"demo.gif: {len(frames)} frames, {size:.2f} MB")
    save_settings_shots(ctrl)
    save_toast_shot(ctrl)
    save_skin_grid()
    print("wrote:", ", ".join(sorted(p.name for p in DOCS.iterdir())))
    return 0 if size <= MAX_GIF_MB else 1


if __name__ == "__main__":
    sys.exit(main())
