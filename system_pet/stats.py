"""System statistics that drive the pet's mood."""
from dataclasses import dataclass

import psutil


@dataclass
class Stats:
    cpu: float = 0.0       # percent
    ram: float = 0.0       # percent
    battery: float | None = None  # percent, None on desktops
    charging: bool = True


def read_stats() -> Stats:
    battery = psutil.sensors_battery()
    return Stats(
        cpu=psutil.cpu_percent(interval=None),
        ram=psutil.virtual_memory().percent,
        battery=battery.percent if battery else None,
        charging=battery.power_plugged if battery else True,
    )


def mood_from(stats: Stats) -> str:
    """Return one of: sick, hot, hungry, happy."""
    if stats.ram > 90:
        return "sick"
    if stats.cpu > 80:
        return "hot"
    if stats.battery is not None and stats.battery < 20 and not stats.charging:
        return "hungry"
    return "happy"
