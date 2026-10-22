"""System-tray icon that mirrors the pet's right-click menu."""
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QSystemTrayIcon

from ..render import icon_pixmap


class Tray:
    def __init__(self, ctrl):
        self.ctrl = ctrl
        self.icon = None
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.menu = ctrl.build_menu(None)
        self.icon = QSystemTrayIcon(QIcon(icon_pixmap(ctrl.store.s)))
        self.icon.setToolTip("System Pet")
        self.icon.setContextMenu(self.menu)
        self.icon.activated.connect(self._activated)
        self.icon.show()
        ctrl.store.changed.connect(self.refresh)

    def _activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.ctrl.open_settings()

    def refresh(self):
        self.icon.setIcon(QIcon(icon_pixmap(self.ctrl.store.s)))
