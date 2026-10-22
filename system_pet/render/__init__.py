"""Renderer discovery. Skins live in <project>/skins and ~/.config/system-pet/skins."""
import json

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QPixmap

from ..paths import config_dir, resource_dir
from .drawn import DrawnRenderer
from .sprite import SpriteRenderer
from .view import BASE, View


_cache: dict[str, object] = {}


def _dirs():
    return [resource_dir() / "skins", config_dir() / "skins"]


def discover_skins(reload: bool = False) -> dict[str, str]:
    """Return {skin key: display name} for every valid skin folder."""
    if reload:
        _cache.clear()
    found = {}
    for root in _dirs():
        if not root.is_dir():
            continue
        for folder in sorted(root.iterdir()):
            meta = folder / "skin.json"
            if meta.is_file():
                try:
                    found[folder.name] = json.loads(meta.read_text()).get("name", folder.name)
                except (OSError, ValueError):
                    pass
    return found


def make_renderer(settings):
    if settings.skin != "drawn":
        if settings.skin in _cache:
            return _cache[settings.skin]
        for root in _dirs():
            folder = root / settings.skin
            if (folder / "skin.json").is_file():
                try:
                    _cache[settings.skin] = SpriteRenderer(folder)
                    return _cache[settings.skin]
                except (OSError, ValueError, KeyError):
                    break
    return DrawnRenderer()


def icon_pixmap(settings, px: int = 64) -> QPixmap:
    from PyQt6.QtGui import QColor
    pm = QPixmap(px, px)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.scale(px / BASE, px / BASE)
    make_renderer(settings).paint(p, View(color=QColor(settings.color), accessory=settings.accessory))
    p.end()
    return pm
