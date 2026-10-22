"""Start the pet automatically on login: XDG autostart entry on Linux, Run registry key on Windows."""
import os
import shlex
import subprocess
import sys
from pathlib import Path

from .paths import is_frozen

MAIN = Path(__file__).resolve().parents[1] / "main.py"
WIN_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
WIN_VALUE = "SystemPet"


def _command() -> list[str]:
    """Command line that launches the app, whether built (PyInstaller) or run from source."""
    if is_frozen():
        return [sys.executable]
    exe = sys.executable
    if sys.platform == "win32":    # pythonw.exe avoids a console window
        pythonw = Path(exe).with_name("pythonw.exe")
        if pythonw.exists():
            exe = str(pythonw)
    return [exe, str(MAIN)]


# ----- Linux -----
def _desktop_path() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "autostart" / "system-pet.desktop"


# ----- public API -----
def is_enabled() -> bool:
    if sys.platform == "win32":
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, WIN_RUN_KEY) as key:
                winreg.QueryValueEx(key, WIN_VALUE)
            return True
        except OSError:
            return False
    return _desktop_path().exists()


def set_enabled(enabled: bool):
    if sys.platform == "win32":
        import winreg
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, WIN_RUN_KEY) as key:
            if enabled:
                winreg.SetValueEx(key, WIN_VALUE, 0, winreg.REG_SZ, subprocess.list2cmdline(_command()))
            else:
                try:
                    winreg.DeleteValue(key, WIN_VALUE)
                except OSError:
                    pass
        return
    p = _desktop_path()
    if not enabled:
        p.unlink(missing_ok=True)
        return
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        "[Desktop Entry]\nType=Application\nName=System Pet\n"
        f"Exec={' '.join(shlex.quote(c) for c in _command())}\n"
        "X-GNOME-Autostart-enabled=true\n")
