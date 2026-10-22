"""Speech bubble that floats above a pet and ignores mouse clicks."""
from PyQt6.QtCore import QRect, Qt, QTimer
from PyQt6.QtGui import QColor, QFontMetrics, QPainter, QPen, QPolygon
from PyQt6.QtCore import QPoint
from PyQt6.QtWidgets import QApplication, QWidget

PAD = 9
TAIL = 10
MAX_TEXT_W = 210


class Bubble(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowTransparentForInput)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.text = ""
        self._text_rect = QRect()
        self._anchor = QRect()
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide)

    def say(self, text: str, anchor: QRect, ms: int = 4500):
        self.text = text
        fm = QFontMetrics(self.font())
        self._text_rect = fm.boundingRect(QRect(0, 0, MAX_TEXT_W, 1000), Qt.TextFlag.TextWordWrap, text)
        self.setFixedSize(self._text_rect.width() + 2 * PAD, self._text_rect.height() + 2 * PAD + TAIL)
        self._anchor = anchor
        self.show()
        self.follow(anchor)
        self._hide_timer.start(ms)

    def follow(self, anchor: QRect):
        if not self.isVisible():
            return
        screen = QApplication.primaryScreen().availableGeometry()
        x = anchor.center().x() - self.width() // 2
        y = anchor.top() - self.height() + 14
        x = max(screen.left(), min(x, screen.right() - self.width()))
        y = max(screen.top(), y)
        self.move(x, y)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        body = QRect(1, 1, self.width() - 2, self.height() - TAIL - 2)
        p.setPen(QPen(QColor(70, 60, 60), 1.5))
        p.setBrush(QColor(255, 253, 245))
        p.drawRoundedRect(body, 10, 10)
        cx = self.width() // 2
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPolygon(QPolygon([QPoint(cx - 6, body.bottom() - 1), QPoint(cx + 6, body.bottom() - 1),
                                QPoint(cx, self.height() - 1)]))
        p.setPen(QColor(50, 45, 45))
        p.drawText(QRect(PAD, PAD, self._text_rect.width(), self._text_rect.height()),
                   int(Qt.TextFlag.TextWordWrap), self.text)
        p.end()
