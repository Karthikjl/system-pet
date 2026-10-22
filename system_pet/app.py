"""Controller: owns settings, needs, pets, reminders, tray and the settings window."""
from PyQt6.QtCore import QObject, QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from .config import SettingsStore
from .guard import Guard
from .needs import Needs
from .pet import Pet
from .render import icon_pixmap
from .reminders import Reminders
from .toast import KINDS, Toast


class Controller(QObject):
    def __init__(self):
        super().__init__()
        self.store = SettingsStore()
        self.needs = Needs.load()
        self.pets: list[Pet] = []
        self.settings_window = None
        QApplication.setWindowIcon(QIcon(icon_pixmap(self.store.s)))

        self.reminders = Reminders(self.store)
        self.toast = Toast()
        self.guard = Guard(self.store)
        self.guard.found.connect(self.on_guard)
        self.reminders.message.connect(self.on_reminder)

        self.needs_timer = QTimer(self)
        self.needs_timer.timeout.connect(self._tick_needs)
        self.needs_timer.start(1000)
        self.save_timer = QTimer(self)
        self.save_timer.timeout.connect(self.needs.save)
        self.save_timer.start(30000)

        self.sync_pets()
        self.store.changed.connect(self.sync_pets)
        self.store.changed.connect(self._refresh_icon)

        from .ui.tray import Tray    # imported late: needs a running QApplication
        self.tray = Tray(self)
        QApplication.instance().aboutToQuit.connect(self.shutdown)

    # ----- pets -----
    def _refresh_icon(self):
        QApplication.setWindowIcon(QIcon(icon_pixmap(self.store.s)))

    def sync_pets(self):
        want = self.store.s.pet_count
        while len(self.pets) < want:
            pet = Pet(self, len(self.pets))
            self.pets.append(pet)
            pet.show()
        while len(self.pets) > want:
            self.pets.pop().shutdown()

    def _tick_needs(self):
        self.needs.tick(1.0, any(p.asleep for p in self.pets))

    def on_reminder(self, kind: str, text: str):
        """Make a reminder impossible to miss: pet hops, a card slides in, optional OS notification."""
        for p in self.pets:
            p.alert(text if p.index == 0 else None)
        self.toast.show_message(kind, text)
        if self.store.s.desktop_notify:
            self.notify(KINDS.get(kind, KINDS["info"])[0], text)

    def on_guard(self, text: str):
        """The guard dog found something new: bark, show the card, optionally notify."""
        for p in self.pets:
            p.alert(text if p.index == 0 else None, kind="guard")
        self.toast.show_message("guard", text, 20000)
        if self.store.s.desktop_notify:
            self.notify(KINDS["guard"][0], text)

    def mute_guard(self, seconds: float = 3600.0):
        self.guard.mute(seconds)
        self.say("Guard dog muted for an hour. Zzz...")

    def notify(self, title: str, text: str):
        icon = getattr(getattr(self, "tray", None), "icon", None)
        if icon is not None and QSystemTrayIcon.supportsMessages():
            icon.showMessage(title, text, QSystemTrayIcon.MessageIcon.Information, 8000)

    def test_reminder(self, kind: str):
        samples = {
            "water": "Time for a sip of water! Staying hydrated keeps you sharp.",
            "eye": "Look at something 20 feet away for 20 seconds.",
            "pomo_break": "Focus session done! Take a short break.",
        }
        self.on_reminder(kind, samples.get(kind, "This is how reminders look."))

    def say(self, text: str):
        if self.pets:
            self.pets[0].say(text, 7000)

    # ----- actions (used by the pet menu, tray and settings window) -----
    def feed(self):
        for p in self.pets:
            p.spawn_item("food")

    def play(self):
        for p in self.pets:
            p.spawn_item("ball")

    def nap(self):
        for p in self.pets:
            p.nap()

    def talk(self):
        if self.pets:
            self.pets[0].talk()

    def open_settings(self):
        if self.settings_window is None:
            from .ui.settings_window import SettingsWindow
            self.settings_window = SettingsWindow(self)
        self.settings_window.show()
        self.settings_window.raise_()
        self.settings_window.activateWindow()

    def build_menu(self, parent) -> QMenu:
        menu = QMenu(parent)
        title = menu.addAction(self.store.s.name)
        title.setEnabled(False)
        menu.addSeparator()
        menu.addAction("Feed a fish", self.feed)
        menu.addAction("Play ball", self.play)
        menu.addAction("Take a nap", self.nap)
        menu.addAction("Say something", self.talk)
        menu.addSeparator()
        menu.addAction("Mute guard dog for 1 hour", lambda: self.mute_guard())
        menu.addAction("Settings...", self.open_settings)
        menu.addAction("Quit", QApplication.quit)
        return menu

    def shutdown(self):
        self.needs.save()
        self.toast.close()
        for p in self.pets:
            p.shutdown()
