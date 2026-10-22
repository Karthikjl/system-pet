"""User settings: a dataclass persisted as JSON, with a change signal for live updates."""
import json
from dataclasses import asdict, dataclass, fields

from PyQt6.QtCore import QObject, pyqtSignal

from .paths import config_dir, data_dir  # noqa: F401 (data_dir is re-exported)


@dataclass
class Settings:
    name: str = "Mochi"
    size: int = 120
    speed: float = 1.0
    skin: str = "drawn"
    color: str = "#f5be6e"
    accessory: str = "none"      # none | bow | hat | glasses
    chase: bool = True
    nap: bool = True
    walk_on_windows: bool = True
    scare: bool = True
    pet_count: int = 1
    water_enabled: bool = True
    water_min: int = 45
    eye_enabled: bool = True
    eye_min: int = 20
    pomo_enabled: bool = False
    pomo_work: int = 25
    pomo_break: int = 5
    alerts: bool = True
    desktop_notify: bool = True
    guard_enabled: bool = False      # opt-in
    guard_ports: bool = True
    guard_devices: bool = True
    guard_interval: int = 15
    autostart: bool = False


class SettingsStore(QObject):
    changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.path = config_dir() / "config.json"
        self.s = self._load()

    def _load(self) -> Settings:
        s = Settings()
        try:
            raw = json.loads(self.path.read_text())
        except (OSError, ValueError):
            return s
        for f in fields(Settings):
            if f.name in raw:
                try:
                    setattr(s, f.name, type(getattr(s, f.name))(raw[f.name]))
                except (TypeError, ValueError):
                    pass
        return s

    def save(self):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(asdict(self.s), indent=2))
        except OSError:
            pass

    def update(self, **kw):
        for k, v in kw.items():
            setattr(self.s, k, v)
        self.save()
        self.changed.emit()
