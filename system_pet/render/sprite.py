"""Renderer for sprite-sheet skins: a folder with skin.json and PNG frames (facing right)."""
import json
from pathlib import Path

from PyQt6.QtCore import QRectF
from PyQt6.QtGui import QPainter, QPixmap

from .drawn import paint_overlays
from .view import BASE, View

KNOWN_STATES = {"idle", "walk", "chase", "fetch", "eat", "sleep", "scared", "drag", "fall", "alert"}

# A skin only has to provide "idle"; other states fall back along this table.
FALLBACK = {"chase": "walk", "fetch": "walk", "eat": "idle", "scared": "idle",
            "drag": "idle", "fall": "idle", "sleep": "idle", "alert": "idle"}


class SpriteRenderer:
    def __init__(self, folder: Path):
        data = json.loads((folder / "skin.json").read_text())
        self.name = data.get("name", folder.name)
        self.fps = float(data.get("fps", 8))
        self.frames: dict[str, list[QPixmap]] = {}
        for state, files in data["frames"].items():
            pixmaps = [QPixmap(str(folder / f)) for f in files]
            pixmaps = [pm for pm in pixmaps if not pm.isNull()]
            if pixmaps:
                self.frames[state] = pixmaps
        if "idle" not in self.frames:
            raise ValueError(f"skin {folder.name} has no usable 'idle' frames")

    def _frames_for(self, state: str):
        return (self.frames.get(state)
                or self.frames.get(FALLBACK.get(state, "idle"))
                or self.frames["idle"])

    def paint(self, p: QPainter, v: View):
        frames = self._frames_for(v.state)
        pm = frames[int(v.now * self.fps) % len(frames)]
        p.save()
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.translate(BASE / 2, 0)
        p.scale(v.facing, 1)
        p.drawPixmap(QRectF(-BASE / 2, 0, BASE, BASE), pm, QRectF(pm.rect()))
        p.restore()
        paint_overlays(p, v)
