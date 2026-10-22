"""System Pet entry point (Windows and Linux)."""
import os
import sys

# Wayland forbids client-side window positioning / always-on-top, so run via XWayland.
if sys.platform.startswith("linux") and os.environ.get("XDG_SESSION_TYPE") == "wayland" \
        and "QT_QPA_PLATFORM" not in os.environ:
    os.environ["QT_QPA_PLATFORM"] = "xcb"


def check() -> int:
    """`--check`: print what the app sees on this machine and exit (useful for bug reports)."""
    from system_pet.paths import config_dir, data_dir, is_frozen, resource_dir
    from system_pet.render import discover_skins
    print("platform :", sys.platform, "| frozen:", is_frozen())
    print("session  :", os.environ.get("XDG_SESSION_TYPE", "n/a"), "| qt platform:",
          os.environ.get("QT_QPA_PLATFORM", "auto"))
    print("resources:", resource_dir())
    print("config   :", config_dir())
    print("data     :", data_dir())
    print("skins    :", ", ".join(discover_skins()) or "none")
    return 0


def main() -> int:
    if "--check" in sys.argv:
        return check()

    from PyQt6.QtCore import QLockFile
    from PyQt6.QtWidgets import QApplication

    from system_pet.paths import data_dir

    if sys.platform == "win32":   # give the taskbar/tray our own identity instead of python.exe's
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("SystemPet.Desktop.Pet")
        except Exception:
            pass

    app = QApplication(sys.argv)
    app.setApplicationName("System Pet")
    app.setQuitOnLastWindowClosed(False)   # the tray/menu keeps the app alive

    # Only one pet manager at a time, otherwise you get two stacks of pets and tray icons.
    data_dir().mkdir(parents=True, exist_ok=True)
    lock = QLockFile(str(data_dir() / "system-pet.lock"))
    if not lock.tryLock(100):
        print("System Pet is already running.")
        return 0

    from system_pet.app import Controller
    ctrl = Controller()                    # noqa: F841 (kept alive for the event loop)
    code = app.exec()
    lock.unlock()
    return code


if __name__ == "__main__":
    sys.exit(main())
