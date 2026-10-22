"""Where things live on each OS, and where bundled resources are when running as a built app."""
import os
import sys
from pathlib import Path

APP_DIR_WINDOWS = "SystemPet"
APP_DIR_UNIX = "system-pet"


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def resource_dir() -> Path:
    """Folder that contains skins/ and assets/ (the PyInstaller bundle, or the project root)."""
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parents[1]


def config_dir() -> Path:
    override = os.environ.get("SYSTEM_PET_CONFIG_DIR")
    if override:
        return Path(override)
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming") / APP_DIR_WINDOWS
    return Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / APP_DIR_UNIX


def data_dir() -> Path:
    override = os.environ.get("SYSTEM_PET_DATA_DIR")
    if override:
        return Path(override)
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local") / APP_DIR_WINDOWS
    return Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / APP_DIR_UNIX
