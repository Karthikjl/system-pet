"""Network guard dog: passive detection of new LAN devices and new listening ports.

Passive means it only reads this computer's existing ARP table and socket list. It never scans the
network and nothing leaves the machine.
"""
import json
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import psutil
from PyQt6.QtCore import QObject, QRunnable, QThreadPool, QTimer, pyqtSignal

from .paths import data_dir

MAC_RE = re.compile(r"(?:[0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}")
IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
MIN_INTERVAL = 20.0      # seconds between two alerts; findings in between are merged into one


# ---------- parsing (pure functions) ----------
def _norm_mac(mac: str) -> str:
    return mac.lower().replace("-", ":")


def _usable(ip: str, mac: str) -> bool:
    """Drop broadcast/multicast entries and the all-zero placeholder MAC."""
    first = int(ip.split(".")[0])
    if 224 <= first <= 239 or ip.endswith(".255"):
        return False
    return mac not in ("00:00:00:00:00:00", "ff:ff:ff:ff:ff:ff") and not mac.startswith("01:00:5e")


def parse_proc_net_arp(text: str) -> dict[str, str]:
    """Linux /proc/net/arp -> {mac: ip}. Flag 0x0 means an incomplete entry."""
    devices = {}
    for line in text.splitlines()[1:]:
        cols = line.split()
        if len(cols) < 4 or cols[2] == "0x0" or not IP_RE.fullmatch(cols[0]):
            continue
        mac = _norm_mac(cols[3])
        if MAC_RE.fullmatch(mac) and _usable(cols[0], mac):
            devices[mac] = cols[0]
    return devices


def parse_arp_a(text: str) -> dict[str, str]:
    """Windows `arp -a` -> {mac: ip}. Matches IP and MAC only, so it works in any language."""
    devices = {}
    for line in text.splitlines():
        ip, mac = IP_RE.search(line), MAC_RE.search(line)
        if ip and mac:
            m = _norm_mac(mac.group())
            if _usable(ip.group(), m):
                devices[m] = ip.group()
    return devices


def read_devices() -> dict[str, str]:
    try:
        if sys.platform.startswith("linux"):
            return parse_proc_net_arp(Path("/proc/net/arp").read_text())
        if sys.platform == "win32":
            out = subprocess.run(["arp", "-a"], capture_output=True, text=True, timeout=10,
                                 creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout
            return parse_arp_a(out)
    except (OSError, subprocess.SubprocessError):
        pass
    return {}


@dataclass
class Listener:
    port: int
    process: str
    local_only: bool


def snapshot_listeners() -> dict[int, Listener]:
    """Every TCP/UDP port something on this computer is listening on, keyed by port."""
    found: dict[int, Listener] = {}
    try:
        conns = psutil.net_connections(kind="inet")
    except (psutil.Error, OSError):
        return found
    for c in conns:
        if c.status != psutil.CONN_LISTEN or not c.laddr:
            continue
        loopback = c.laddr.ip.startswith("127.") or c.laddr.ip == "::1"
        name = "unknown program"
        if c.pid:
            try:
                name = psutil.Process(c.pid).name()
            except psutil.Error:
                pass
        old = found.get(c.laddr.port)
        if old is None:
            found[c.laddr.port] = Listener(c.laddr.port, name, loopback)
        else:                                    # same port on several addresses: exposed if any is
            old.local_only = old.local_only and loopback
            if old.process == "unknown program":
                old.process = name
    return found


# ---------- decision logic (no Qt, easy to test) ----------
@dataclass
class Finding:
    kind: str       # "device" | "port"
    text: str


class Detector:
    def __init__(self, known_devices: dict[str, str] | None = None):
        self.devices = dict(known_devices or {})
        self._learn_devices = not self.devices     # first run: learn what is normal without barking
        self.ports: set[int] | None = None         # None until the first scan (the baseline)

    def scan(self, devices: dict[str, str], listeners: dict[int, Listener],
             want_devices: bool = True, want_ports: bool = True) -> list[Finding]:
        out = []
        if want_devices:
            for mac in devices:
                if mac not in self.devices and not self._learn_devices:
                    out.append(Finding("device", f"New device on your network: {devices[mac]} ({mac})"))
            self.devices.update(devices)
            if devices:
                self._learn_devices = False
        if want_ports:
            if self.ports is None:
                self.ports = set(listeners)
            else:
                for port in sorted(set(listeners) - self.ports):
                    ln = listeners[port]
                    scope = "local only" if ln.local_only else "reachable from your network"
                    out.append(Finding("port", f"New listener on port {port}: {ln.process} ({scope})"))
                self.ports |= set(listeners)
        return out


class Throttle:
    """Merges findings into at most one message per MIN_INTERVAL (the card shows one message at a time)."""

    def __init__(self):
        self.pending: list[Finding] = []
        self.last = -1e9

    def offer(self, findings: list[Finding], now: float) -> str | None:
        self.pending.extend(findings)
        if not self.pending or now - self.last < MIN_INTERVAL:
            return None
        items, self.pending = self.pending, []
        self.last = now
        if len(items) == 1:
            return items[0].text
        return f"{len(items)} new things detected. First: {items[0].text}"


# ---------- Qt glue ----------
def _devices_file() -> Path:
    return data_dir() / "known_devices.json"


def load_known_devices() -> dict[str, str]:
    try:
        raw = json.loads(_devices_file().read_text())
        return {str(k): str(v) for k, v in raw.items()}
    except (OSError, ValueError, AttributeError):
        return {}


def save_known_devices(devices: dict[str, str]):
    try:
        _devices_file().parent.mkdir(parents=True, exist_ok=True)
        _devices_file().write_text(json.dumps(devices, indent=2))
    except OSError:
        pass


class _Signals(QObject):
    done = pyqtSignal(object, object)


class _ScanJob(QRunnable):
    def __init__(self, signals: _Signals):
        super().__init__()
        self.signals = signals

    def run(self):
        self.signals.done.emit(read_devices(), snapshot_listeners())


class Guard(QObject):
    found = pyqtSignal(str)

    def __init__(self, store):
        super().__init__()
        self.store = store
        self.muted_until = 0.0
        self._scanning = False
        self._reset_detector()
        self._signals = _Signals()
        self._signals.done.connect(self._on_scan)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._scan)
        store.changed.connect(self.apply_settings)
        self.apply_settings()

    def _reset_detector(self):
        self.detector = Detector(load_known_devices())
        self.throttle = Throttle()

    def apply_settings(self):
        s = self.store.s
        self.timer.setInterval(max(5, s.guard_interval) * 1000)
        if s.guard_enabled and not self.timer.isActive():
            self._reset_detector()
            self.timer.start()
            QTimer.singleShot(0, self._scan)
        elif not s.guard_enabled and self.timer.isActive():
            self.timer.stop()

    def _scan(self):
        if self._scanning:
            return
        self._scanning = True
        QThreadPool.globalInstance().start(_ScanJob(self._signals))

    def _on_scan(self, devices, listeners):
        self._scanning = False
        s = self.store.s
        if not s.guard_enabled:
            return
        before = dict(self.detector.devices)
        findings = self.detector.scan(devices, listeners, s.guard_devices, s.guard_ports)
        if self.detector.devices != before:
            save_known_devices(self.detector.devices)
        now = time.monotonic()
        message = self.throttle.offer(findings, now)
        if message and not self.is_muted():
            self.found.emit(message)

    # ----- controls used by the UI -----
    def is_muted(self) -> bool:
        return time.monotonic() < self.muted_until

    def mute(self, seconds: float = 3600.0):
        self.muted_until = time.monotonic() + seconds

    def unmute(self):
        self.muted_until = 0.0

    def known_device_count(self) -> int:
        return len(self.detector.devices)

    def forget_devices(self):
        try:
            _devices_file().unlink(missing_ok=True)
        except OSError:
            pass
        self._reset_detector()
