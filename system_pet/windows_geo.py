"""Find the tops of other windows so the pet can stand on them (X11 and Windows only).

Wayland does not let applications see other windows, so the feature switches itself off there.
"""
import os
import sys

from PyQt6.QtCore import QObject, QTimer
from PyQt6.QtWidgets import QApplication

MIN_W, MIN_H = 120, 50
REFRESH_MS = 250


def floor_y(x: float, feet_y: float, surfaces, screen_bottom: float, tolerance: float = 8.0) -> float:
    """Y of the surface the pet would stand on at x: the highest one at or below its feet.

    `surfaces` holds (left, top, right) tuples. Surfaces above the feet are ignored, so a pet never
    teleports up onto a window; it gets there by being dragged or thrown.
    """
    best = screen_bottom
    for left, top, right in surfaces:
        if left <= x <= right and feet_y - tolerance <= top < best:
            best = top
    return best


def unsupported_reason() -> str | None:
    """None when walking on windows can work here, otherwise a short human-readable reason."""
    if sys.platform == "win32":
        return None
    if not sys.platform.startswith("linux"):
        return "only Windows and Linux (X11) are supported"
    if os.environ.get("XDG_SESSION_TYPE") == "wayland":
        return "Wayland does not let apps see other windows (use an X11 session)"
    if not os.environ.get("DISPLAY"):
        return "no X11 display found"
    try:
        import Xlib  # noqa: F401
    except ImportError:
        return "python-xlib is not installed"
    return None


# ---------- Linux / X11 ----------
class _X11Backend:
    def __init__(self):
        from Xlib import X, display
        self.X = X
        self.d = display.Display()
        self.root = self.d.screen().root
        atom = self.d.intern_atom
        self.a_list = atom("_NET_CLIENT_LIST_STACKING")
        self.a_state = atom("_NET_WM_STATE")
        self.a_hidden = atom("_NET_WM_STATE_HIDDEN")
        self.a_fullscreen = atom("_NET_WM_STATE_FULLSCREEN")
        self.a_type = atom("_NET_WM_WINDOW_TYPE")
        self.skip_types = {atom("_NET_WM_WINDOW_TYPE_DESKTOP"), atom("_NET_WM_WINDOW_TYPE_DOCK")}
        self.a_pid = atom("_NET_WM_PID")
        self.a_extents = atom("_NET_FRAME_EXTENTS")

    def _prop(self, win, atom):
        p = win.get_full_property(atom, self.X.AnyPropertyType)
        return list(p.value) if p is not None else None

    def _window_ids(self):
        ids = self._prop(self.root, self.a_list)
        if ids:
            return ids
        # No window manager (or one without EWMH): fall back to the root's direct children.
        return [w.id for w in self.root.query_tree().children]

    def rects(self, my_pid: int):
        out = []
        for wid in self._window_ids():
            try:
                win = self.d.create_resource_object("window", wid)
                attrs = win.get_attributes()
                if attrs.map_state != self.X.IsViewable or attrs.override_redirect:
                    continue
                states = self._prop(win, self.a_state) or []
                if self.a_hidden in states or self.a_fullscreen in states:
                    continue
                if self.skip_types & set(self._prop(win, self.a_type) or []):
                    continue
                pid = self._prop(win, self.a_pid)
                if pid and pid[0] == my_pid:                   # our own pets, bubbles and cards
                    continue
                geo = win.get_geometry()
                pos = self.root.translate_coords(win, 0, 0)
                left, top, w, h = pos.x, pos.y, geo.width, geo.height
                ext = self._prop(win, self.a_extents)          # left, right, top, bottom of the frame
                if ext and len(ext) >= 4:
                    left, top = left - ext[0], top - ext[2]
                    w, h = w + ext[0] + ext[1], h + ext[2] + ext[3]
                out.append((left, top, w, h))
            except Exception:
                continue                                       # window vanished mid-query
        return out


# ---------- Windows ----------
class _WinBackend:
    def __init__(self):
        import ctypes
        from ctypes import wintypes
        self.ctypes, self.wintypes = ctypes, wintypes
        self.user32 = ctypes.windll.user32
        self.dwm = ctypes.windll.dwmapi
        self.skip_classes = {"Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd"}

    def rects(self, my_pid: int):
        ct, wt, user32, dwm = self.ctypes, self.wintypes, self.user32, self.dwm
        out = []

        @ct.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
        def visit(hwnd, _lparam):
            try:
                if not user32.IsWindowVisible(hwnd) or user32.IsIconic(hwnd):
                    return True
                if user32.GetWindowTextLengthW(hwnd) == 0:
                    return True
                if user32.GetWindowLongW(hwnd, -20) & 0x80:            # WS_EX_TOOLWINDOW
                    return True
                pid = wt.DWORD()
                user32.GetWindowThreadProcessId(hwnd, ct.byref(pid))
                if pid.value == my_pid:
                    return True
                cls = ct.create_unicode_buffer(64)
                user32.GetClassNameW(hwnd, cls, 64)
                if cls.value in self.skip_classes:
                    return True
                cloaked = wt.DWORD()
                dwm.DwmGetWindowAttribute(hwnd, 14, ct.byref(cloaked), 4)   # DWMWA_CLOAKED
                if cloaked.value:
                    return True
                r = wt.RECT()
                if dwm.DwmGetWindowAttribute(hwnd, 9, ct.byref(r), ct.sizeof(r)) != 0:  # extended frame
                    user32.GetWindowRect(hwnd, ct.byref(r))
                out.append((r.left, r.top, r.right - r.left, r.bottom - r.top))
            except Exception:
                pass
            return True

        user32.EnumWindows(visit, 0)
        return out


def _make_backend():
    return _WinBackend() if sys.platform == "win32" else _X11Backend()


class WindowWatcher(QObject):
    """Keeps an up-to-date list of window tops (Qt logical pixels) for the pets to stand on."""

    def __init__(self, store):
        super().__init__()
        self.store = store
        self.surfaces: list[tuple[float, float, float]] = []
        self._backend = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        store.changed.connect(self.apply_settings)
        self.apply_settings()

    def apply_settings(self):
        want = self.store.s.walk_on_windows and unsupported_reason() is None
        if want and not self.timer.isActive():
            try:
                self._backend = _make_backend()
            except Exception:
                self._backend = None
            if self._backend is not None:
                self.timer.start(REFRESH_MS)
                self.refresh()
        elif not want and self.timer.isActive():
            self.timer.stop()
            self.surfaces = []

    def refresh(self):
        try:
            rects = self._backend.rects(os.getpid())
        except Exception:
            rects = []
        screen = QApplication.primaryScreen()
        dpr = screen.devicePixelRatio() or 1.0
        area = screen.availableGeometry()
        out = []
        for x, y, w, h in rects:
            x, y, w, h = x / dpr, y / dpr, w / dpr, h / dpr
            if w >= MIN_W and h >= MIN_H and area.top() + 5 < y < area.bottom() - 20:
                out.append((x, y, x + w))
        self.surfaces = out
