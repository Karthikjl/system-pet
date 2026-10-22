"""Tabbed settings dialog. Every control writes straight to the store, so changes apply live."""
import time

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import (QCheckBox, QColorDialog, QComboBox, QDialog, QFormLayout, QGroupBox,
                             QHBoxLayout, QLabel, QLineEdit, QProgressBar, QPushButton, QSlider,
                             QSpinBox, QTabWidget, QVBoxLayout, QWidget)

from .. import autostart
from ..render import discover_skins, make_renderer
from ..render.view import BASE, View
from ..stats import read_stats


class Preview(QWidget):
    """Live animated preview of the current look."""

    def __init__(self, store):
        super().__init__()
        self.store = store
        self.setFixedSize(170, 170)
        self.renderer = make_renderer(store.s)
        store.changed.connect(self._refresh)
        self.phase = 0.0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._step)
        self.timer.start(40)

    def _refresh(self):
        self.renderer = make_renderer(self.store.s)

    def _step(self):
        self.phase += 0.25
        self.update()

    def paintEvent(self, _):
        s = self.store.s
        walking = int(time.monotonic() / 3) % 2 == 0
        v = View(state="walk" if walking else "idle", phase=self.phase, now=time.monotonic(),
                 color=QColor(s.color), accessory=s.accessory)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor(235, 235, 240))
        p.scale(self.width() / BASE * 0.95, self.height() / BASE * 0.95)
        p.translate(3, 3)
        self.renderer.paint(p, v)
        p.end()


class SettingsWindow(QDialog):
    def __init__(self, ctrl):
        super().__init__()
        self.ctrl = ctrl
        self.store = ctrl.store
        self.setWindowTitle("System Pet Settings")
        self.setMinimumWidth(520)

        tabs = QTabWidget()
        tabs.addTab(self._appearance_tab(), "Appearance")
        tabs.addTab(self._behaviour_tab(), "Behaviour")
        tabs.addTab(self._reminders_tab(), "Reminders")
        tabs.addTab(self._system_tab(), "System")
        tabs.addTab(self._about_tab(), "About")
        lay = QVBoxLayout(self)
        lay.addWidget(tabs)

        self.live = QTimer(self)
        self.live.timeout.connect(self._refresh_live)
        self.live.start(1000)
        self._refresh_live()

    # ----- helpers -----
    def _check(self, text, key):
        cb = QCheckBox(text)
        cb.setChecked(getattr(self.store.s, key))
        cb.toggled.connect(lambda v, k=key: self.store.update(**{k: v}))
        return cb

    def _spin(self, key, lo, hi, suffix=""):
        sp = QSpinBox()
        sp.setRange(lo, hi)
        sp.setSuffix(suffix)
        sp.setValue(getattr(self.store.s, key))
        sp.valueChanged.connect(lambda v, k=key: self.store.update(**{k: v}))
        return sp

    def _slider(self, lo, hi, value, on_change, fmt):
        row = QHBoxLayout()
        sl = QSlider(Qt.Orientation.Horizontal)
        sl.setRange(lo, hi)
        sl.setValue(value)
        lbl = QLabel(fmt(value))
        lbl.setMinimumWidth(48)
        sl.valueChanged.connect(lambda v: (lbl.setText(fmt(v)), on_change(v)))
        row.addWidget(sl)
        row.addWidget(lbl)
        return row

    # ----- tabs -----
    def _appearance_tab(self):
        s = self.store.s
        w = QWidget()
        form = QFormLayout()

        name = QLineEdit(s.name)
        name.editingFinished.connect(lambda: self.store.update(name=name.text().strip() or "Pet"))
        form.addRow("Name", name)

        form.addRow("Size", self._slider(60, 240, s.size, lambda v: self.store.update(size=v),
                                         lambda v: f"{v}px"))

        self.skin_box = QComboBox()
        self.skin_box.setMinimumWidth(190)
        self._fill_skins()
        self.skin_box.currentIndexChanged.connect(
            lambda _: self.store.update(skin=self.skin_box.currentData()))
        reload_btn = QPushButton("Reload skins")
        reload_btn.clicked.connect(self._reload_skins)
        row = QHBoxLayout()
        row.addWidget(self.skin_box, 1)
        row.addWidget(reload_btn)
        form.addRow("Skin", row)

        self.color_btn = QPushButton()
        self._paint_color_button()
        self.color_btn.clicked.connect(self._pick_color)
        form.addRow("Colour (drawn cat)", self.color_btn)

        acc = QComboBox()
        for label, key in (("None", "none"), ("Bow", "bow"), ("Party hat", "hat"), ("Glasses", "glasses")):
            acc.addItem(label, key)
        acc.setCurrentIndex(max(0, acc.findData(s.accessory)))
        acc.currentIndexChanged.connect(lambda _: self.store.update(accessory=acc.currentData()))
        form.addRow("Accessory (drawn cat)", acc)

        hint = QLabel("Add your own skins to ~/.config/system-pet/skins/<name>/ (see README).")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: gray;")
        form.addRow(hint)

        lay = QHBoxLayout(w)
        lay.addLayout(form, 1)
        lay.addWidget(Preview(self.store), 0, Qt.AlignmentFlag.AlignTop)
        return w

    def _fill_skins(self):
        self.skin_box.blockSignals(True)
        self.skin_box.clear()
        self.skin_box.addItem("Drawn cat (customizable)", "drawn")
        for key, title in discover_skins().items():
            self.skin_box.addItem(title, key)
        self.skin_box.setCurrentIndex(max(0, self.skin_box.findData(self.store.s.skin)))
        self.skin_box.blockSignals(False)

    def _reload_skins(self):
        discover_skins(reload=True)
        self._fill_skins()
        self.store.update(skin=self.skin_box.currentData())

    def _paint_color_button(self):
        c = self.store.s.color
        self.color_btn.setText(c)
        self.color_btn.setStyleSheet(f"background-color: {c}; padding: 4px;")

    def _pick_color(self):
        c = QColorDialog.getColor(QColor(self.store.s.color), self, "Pet colour")
        if c.isValid():
            self.store.update(color=c.name())
            self._paint_color_button()

    def _behaviour_tab(self):
        s = self.store.s
        w = QWidget()
        form = QFormLayout(w)
        form.addRow("Speed", self._slider(3, 25, int(s.speed * 10),
                                          lambda v: self.store.update(speed=v / 10),
                                          lambda v: f"{v / 10:.1f}x"))
        form.addRow(self._check("Chase the cursor", "chase"))
        form.addRow(self._check("Take naps on its own", "nap"))
        form.addRow(self._check("Get scared by fast mouse movement", "scare"))
        form.addRow("Number of pets", self._spin("pet_count", 1, 5))
        return w

    def _reminders_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        for title, enabled, rows in (
            ("Drink water", "water_enabled", (("Every", "water_min", 1, 240, " min"),)),
            ("Rest your eyes (20-20-20)", "eye_enabled", (("Every", "eye_min", 1, 120, " min"),)),
            ("Pomodoro timer", "pomo_enabled", (("Work", "pomo_work", 1, 120, " min"),
                                                ("Break", "pomo_break", 1, 60, " min"))),
        ):
            box = QGroupBox()
            form = QFormLayout(box)
            form.addRow(self._check(title, enabled))
            for label, key, lo, hi, suf in rows:
                form.addRow(label, self._spin(key, lo, hi, suf))
            lay.addWidget(box)
        lay.addWidget(self._check("Also send a desktop notification", "desktop_notify"))

        demo = QGroupBox("Preview how a reminder looks")
        row = QHBoxLayout(demo)
        for text, kind in (("Water", "water"), ("Eyes", "eye"), ("Pomodoro", "pomo_break")):
            b = QPushButton(text)
            b.clicked.connect(lambda _=False, k=kind: self.ctrl.test_reminder(k))
            row.addWidget(b)
        lay.addWidget(demo)
        lay.addStretch(1)
        return w

    def _system_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addWidget(self._check("Warn me when CPU/RAM is high or my pet needs something", "alerts"))
        auto = QCheckBox("Start System Pet when I log in")
        auto.setChecked(autostart.is_enabled())
        auto.toggled.connect(lambda v: (autostart.set_enabled(v), self.store.update(autostart=v)))
        lay.addWidget(auto)

        box = QGroupBox("Live status")
        form = QFormLayout(box)
        self.sys_label = QLabel()
        form.addRow("System", self.sys_label)
        self.bars = {}
        for key, label in (("fullness", "Fullness"), ("energy", "Energy"), ("happiness", "Happiness")):
            bar = QProgressBar()
            bar.setRange(0, 100)
            self.bars[key] = bar
            form.addRow(label, bar)
        lay.addWidget(box)

        row = QHBoxLayout()
        for text, fn in (("Feed", self.ctrl.feed), ("Play ball", self.ctrl.play), ("Nap", self.ctrl.nap)):
            b = QPushButton(text)
            b.clicked.connect(lambda _=False, f=fn: f())
            row.addWidget(b)
        lay.addLayout(row)
        lay.addStretch(1)
        return w

    def _about_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lbl = QLabel(
            "<h3>System Pet</h3>"
            "<p>A desktop pet that reacts to your mouse and your system.</p>"
            "<ul><li>Click to pet, drag to carry, release to throw</li>"
            "<li>Double-click to chat; right-click for the menu</li>"
            "<li>Feed it a fish or play ball from the menu or tray</li></ul>"
            f"<p>Config: {self.store.path}</p>")
        lbl.setWordWrap(True)
        lbl.setTextFormat(Qt.TextFormat.RichText)
        lay.addWidget(lbl)
        lay.addStretch(1)
        return w

    def _refresh_live(self):
        st = read_stats()
        bat = f"{st.battery:.0f}%" if st.battery is not None else "n/a"
        self.sys_label.setText(f"CPU {st.cpu:.0f}%   RAM {st.ram:.0f}%   Battery {bat}")
        n = self.ctrl.needs
        for key, bar in self.bars.items():
            bar.setValue(int(getattr(n, key)))
