"""Water, eye-rest (20-20-20) and Pomodoro reminders, delivered as speech-bubble text."""
from PyQt6.QtCore import QObject, QTimer, pyqtSignal


class Reminders(QObject):
    message = pyqtSignal(str, str)    # (kind, text)

    def __init__(self, store):
        super().__init__()
        self.store = store
        self._cfg = self._current_cfg()
        self.reset()
        store.changed.connect(self._on_settings)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(1000)

    def _current_cfg(self):
        s = self.store.s
        return (s.water_enabled, s.water_min, s.eye_enabled, s.eye_min,
                s.pomo_enabled, s.pomo_work, s.pomo_break)

    def _on_settings(self):
        cfg = self._current_cfg()
        if cfg != self._cfg:       # unrelated setting changes must not restart the timers
            self._cfg = cfg
            self.reset()

    def reset(self):
        s = self.store.s
        self.water_left = s.water_min * 60
        self.eye_left = s.eye_min * 60
        self.pomo_phase = "work"
        self.pomo_left = s.pomo_work * 60

    def tick(self):
        s = self.store.s
        if s.water_enabled:
            self.water_left -= 1
            if self.water_left <= 0:
                self.water_left = s.water_min * 60
                self.message.emit("water", "Time for a sip of water! Staying hydrated keeps you sharp.")
        if s.eye_enabled:
            self.eye_left -= 1
            if self.eye_left <= 0:
                self.eye_left = s.eye_min * 60
                self.message.emit("eye", "Look at something 20 feet away for 20 seconds.")
        if s.pomo_enabled:
            self.pomo_left -= 1
            if self.pomo_left <= 0:
                if self.pomo_phase == "work":
                    self.pomo_phase, self.pomo_left = "break", s.pomo_break * 60
                    self.message.emit("pomo_break", f"Focus session done! Take a {s.pomo_break} min break.")
                else:
                    self.pomo_phase, self.pomo_left = "work", s.pomo_work * 60
                    self.message.emit("pomo_work", f"Break over. Focus for {s.pomo_work} min!")
