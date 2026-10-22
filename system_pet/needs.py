"""Hunger / energy / happiness that decay over time and persist between runs."""
import json
import time

from .config import data_dir

FULLNESS_RATE = 0.8     # points lost per minute
HAPPINESS_RATE = 0.5
ENERGY_DRAIN = 0.4
ENERGY_GAIN = 20.0      # per minute while asleep, so a short nap is actually restful


def _clamp(v: float) -> float:
    return max(0.0, min(100.0, v))


class Needs:
    def __init__(self, fullness=80.0, energy=90.0, happiness=80.0):
        self.fullness = fullness
        self.energy = energy
        self.happiness = happiness

    def tick(self, dt: float, asleep: bool):
        m = dt / 60.0
        self.fullness = _clamp(self.fullness - FULLNESS_RATE * m)
        self.happiness = _clamp(self.happiness - HAPPINESS_RATE * m)
        self.energy = _clamp(self.energy + (ENERGY_GAIN if asleep else -ENERGY_DRAIN) * m)

    def feed(self):
        self.fullness = _clamp(self.fullness + 40)
        self.happiness = _clamp(self.happiness + 5)

    def play(self):
        self.happiness = _clamp(self.happiness + 15)
        self.energy = _clamp(self.energy - 5)

    def pet(self):
        self.happiness = _clamp(self.happiness + 4)

    def mood(self, system_mood: str) -> str:
        """System trouble wins; otherwise the pet's own needs decide."""
        if system_mood != "happy":
            return system_mood
        if self.fullness < 25:
            return "hungry"
        if self.happiness < 25:
            return "sad"
        return "happy"

    # ----- persistence -----
    @staticmethod
    def _path():
        return data_dir() / "state.json"

    @classmethod
    def load(cls) -> "Needs":
        try:
            raw = json.loads(cls._path().read_text())
            n = cls(float(raw["fullness"]), float(raw["energy"]), float(raw["happiness"]))
            minutes = max(0.0, (time.time() - float(raw.get("saved_at", time.time()))) / 60.0)
            # Time spent closed counts, but never leaves the pet in a bad state on launch.
            n.fullness = min(n.fullness, max(n.fullness - FULLNESS_RATE * minutes, 35.0))
            n.happiness = min(n.happiness, max(n.happiness - HAPPINESS_RATE * minutes, 35.0))
            return n
        except (OSError, ValueError, KeyError):
            return cls()

    def save(self):
        try:
            self._path().parent.mkdir(parents=True, exist_ok=True)
            self._path().write_text(json.dumps({
                "fullness": self.fullness, "energy": self.energy,
                "happiness": self.happiness, "saved_at": time.time()}))
        except OSError:
            pass
