"""The pet widget: a transparent always-on-top window with simple physics and behaviour."""
import math
import random
import time

from PyQt6.QtCore import QPointF, Qt, QTimer
from PyQt6.QtGui import QColor, QCursor, QPainter
from PyQt6.QtWidgets import QApplication, QWidget

from .bubble import Bubble
from .items import Item
from .render import make_renderer
from .render.view import BASE, View
from .stats import mood_from, read_stats
from .windows_geo import floor_y

GRAVITY = 1800.0       # px/s^2
WALK_SPEED = 90.0
RUN_SPEED = 260.0
TICK_MS = 16
WALKING = ("walk", "chase", "scared", "fetch")

CHAT = ["Hello!", "Nice day for a nap.", "Got any snacks?", "I'm watching your cursor...",
        "Meow? Oh wait, I'm just a pet.", "Keep going, you're doing great!", "Boop!"]
ALERTS = {
    "hot": "Whew, the CPU is running hot!",
    "sick": "Your RAM is almost full... I don't feel so good.",
    "hungry": "I'm hungry! Right-click me to feed me.",
    "sad": "I'm a bit lonely. Play with me?",
}
ALERT_COOLDOWN = 300.0


class Pet(QWidget):
    def __init__(self, ctrl, index: int = 0):
        super().__init__()
        self.ctrl = ctrl
        self.store = ctrl.store
        self.index = index
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.S = self.store.s.size
        self.setFixedSize(self.S, self.S)
        self.renderer = make_renderer(self.store.s)
        self.bubble = Bubble()
        self.item: Item | None = None
        self.kicks = 0
        self._kick_until = 0.0
        self._nap_after_landing = 0.0
        self._next_hop = 0.0
        self.alert_label = ""
        self._edge_turns: bool | None = None

        self.bounds = QApplication.primaryScreen().availableGeometry()
        # (x, y) is the pet's feet, bottom-center of the widget.
        self.x = float(random.randint(self.bounds.left() + 200, self.bounds.right() - 200))
        self.y = float(self.bounds.top())
        self.vx = 0.0
        self.vy = 0.0
        self.facing = 1

        self.state = "idle"       # idle walk chase fetch eat sleep scared drag fall
        self.state_until = 0.0
        self.walk_dir = 1
        self.phase = 0.0
        self.mood = "happy"
        self.hearts_until = 0.0
        self._alerted: dict[str, float] = {}

        self._drag_offset = QPointF()
        self._drag_history: list[tuple[float, float, float]] = []
        self._press_pos = QPointF()
        self._moved = False
        self._last_cursor = QPointF(QCursor.pos())
        self._cursor_speed = 0.0
        self._last_tick = time.monotonic()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(TICK_MS)

        self.stats_timer = QTimer(self)
        self.stats_timer.timeout.connect(self._update_mood)
        self.stats_timer.start(2000)
        self._update_mood()

        self.store.changed.connect(self.apply_settings)
        self._apply_geometry()

    # ---------- settings / lifecycle ----------
    def apply_settings(self):
        s = self.store.s
        if s.size != self.S:
            self.S = s.size
            self.setFixedSize(self.S, self.S)
        self.renderer = make_renderer(s)
        self.update()

    def shutdown(self):
        try:
            self.store.changed.disconnect(self.apply_settings)
        except TypeError:
            pass
        self.timer.stop()
        self.stats_timer.stop()
        self.clear_item()
        self.bubble.close()
        self.close()

    @property
    def asleep(self) -> bool:
        return self.state == "sleep"

    # ---------- speech ----------
    def say(self, text: str, ms: int = 4500):
        self.bubble.say(text, self.geometry(), ms)

    def talk(self):
        n = self.ctrl.needs
        pool = list(CHAT)
        if n.fullness < 40:
            pool.append("My tummy is rumbling...")
        if n.happiness < 40:
            pool.append("Play with me?")
        self.say(random.choice(pool))

    # ---------- actions ----------
    def spawn_item(self, kind: str):
        self.clear_item()
        it = Item(kind)
        it.x = float(min(max(self.x + random.choice((-1, 1)) * random.randint(120, 300),
                             self.bounds.left() + 30), self.bounds.right() - 30))
        it.y = float(self.bounds.top())
        it.vx = random.uniform(-80, 80) if kind == "ball" else 0.0
        self.item = it
        self.kicks = 0
        it.show()
        if self.state in ("sleep", "idle", "walk"):
            self._set_state("idle", 0.2)

    def clear_item(self):
        if self.item is not None:
            self.item.close()
            self.item.deleteLater()
            self.item = None

    def alert(self, text: str | None = None, seconds: float = 6.0, kind: str = "reminder"):
        """Get the user's attention: hop up and down, wide-eyed, with a bubble."""
        self.alert_label = "WOOF!" if kind == "guard" else ""
        self._nap_after_landing = 0.0
        self._set_state("alert", seconds)
        self._next_hop = 0.0
        if text:
            self.say(text, int(seconds * 1000) + 4000)

    def _floor(self, x: float) -> float:
        """Where the pet stands at x: a window top (if allowed and supported) or the screen bottom."""
        return floor_y(x, self.y, self.ctrl.windows.surfaces, self.bounds.bottom())

    def nap(self, seconds: float = 15.0):
        if self.state in ("drag", "fall") or self.y < self._floor(self.x) - 0.5:
            self._nap_after_landing = seconds      # can't doze off in mid-air
        else:
            self._set_state("sleep", seconds)

    # ---------- behaviour ----------
    def _update_mood(self):
        self.mood = self.ctrl.needs.mood(mood_from(read_stats()))
        if self.index == 0 and self.store.s.alerts and self.mood in ALERTS:
            now = time.monotonic()
            if now - self._alerted.get(self.mood, -1e9) > ALERT_COOLDOWN:
                self._alerted[self.mood] = now
                self.say(ALERTS[self.mood], 6000)

    def _set_state(self, state: str, duration: float = 0.0):
        self.state = state
        self.state_until = time.monotonic() + duration

    def _pick_idle_behaviour(self, now: float):
        s = self.store.s
        roll = random.random()
        if self.ctrl.needs.energy < 20:
            self._set_state("sleep", random.uniform(8.0, 15.0))
        elif roll < 0.35:
            self.walk_dir = random.choice((-1, 1))
            self._set_state("walk", random.uniform(1.5, 4.0))
        elif roll < 0.5 and s.nap and self.mood == "happy":
            self._set_state("sleep", random.uniform(5.0, 12.0))
        else:
            self._set_state("idle", random.uniform(1.5, 4.0))
            if self.index == 0 and random.random() < 0.08:
                self.talk()

    def _think_item(self, now: float) -> bool:
        """Return True when the pet is busy with its food or ball."""
        it = self.item
        if it is None:
            return False
        if it.age > 60:
            self.clear_item()
            return False
        dx = it.x - self.x
        if it.kind == "food":
            if it.on_ground and abs(dx) < 28:
                self.clear_item()
                self.ctrl.needs.feed()
                self.hearts_until = now + 1.8
                self._set_state("eat", 1.5)
                self.say("Yum!", 2000)
                return True
        elif abs(dx) < 34 and it.y > self.y - 70 and now > self._kick_until:
            self._kick_until = now + 0.5
            it.vx = (1 if dx >= 0 else -1) * random.uniform(350, 650)
            it.vy = -random.uniform(350, 600)
            self.kicks += 1
            self.ctrl.needs.play()
            self.hearts_until = now + 1.0
            if self.kicks >= 8:
                self.clear_item()
                self.say("That was fun!", 2500)
                return False
        if abs(dx) > 20:
            self.state = "fetch"
            self.state_until = now + 0.3
        return True

    def _think(self, now: float, dt: float):
        s = self.store.s
        cur = QPointF(QCursor.pos())
        speed = math.hypot(cur.x() - self._last_cursor.x(), cur.y() - self._last_cursor.y()) / max(dt, 1e-3)
        self._cursor_speed = 0.8 * self._cursor_speed + 0.2 * speed
        self._last_cursor = cur

        if self.state in ("drag", "fall"):
            return
        if self.state == "eat":
            if now > self.state_until:
                self._set_state("idle", 1.0)
            return
        if self.state == "alert":
            if now > self.state_until:
                self.alert_label = ""
                self._set_state("idle", 1.0)
            return

        dist = math.hypot(cur.x() - self.x, cur.y() - (self.y - self.S / 2))

        # Scared: cursor whips past very fast and close.
        if s.scare and self._cursor_speed > 2500 and dist < 160 and self.state != "scared":
            self.walk_dir = -1 if cur.x() > self.x else 1
            self._set_state("scared", 1.2)
            self.vy = -500.0
            return

        # A sleeping pet stays asleep until its nap ends (a click, drag or scare still wakes it).
        if self.state == "sleep":
            if now > self.state_until:
                self._set_state("idle", 0.5)
            return
        if self.state == "scared":
            if now > self.state_until:
                self._set_state("idle", 0.5)
            return

        if self._think_item(now):
            return
        if self.state == "fetch":     # the item vanished
            self._set_state("idle", 0.5)

        if s.chase and dist < 500 and self._cursor_speed < 1500 and abs(cur.x() - self.x) > 50:
            self.state = "chase"
            self.state_until = now + 0.3
            return
        if self.state == "chase" and now > self.state_until:
            self._set_state("idle", 1.0)

        if now > self.state_until:
            self._pick_idle_behaviour(now)

    def _tick(self):
        now = time.monotonic()
        dt = min(now - self._last_tick, 0.05)
        self._last_tick = now
        s = self.store.s
        self._think(now, dt)
        if self.item is not None:
            self.item.step(dt, self.bounds)

        ground = self._floor(self.x)
        left, right = self.bounds.left() + self.S / 2, self.bounds.right() - self.S / 2

        if self.state == "drag":
            self.phase += dt * 6
            self.update()
            return

        walk, run = WALK_SPEED * s.speed, RUN_SPEED * s.speed
        target_vx = 0.0
        if self.state == "walk":
            target_vx = self.walk_dir * walk
        elif self.state == "chase":
            target_vx = run * (1 if QCursor.pos().x() > self.x else -1)
        elif self.state == "fetch" and self.item is not None:
            target_vx = run * (1 if self.item.x > self.x else -1)
        elif self.state == "scared":
            target_vx = self.walk_dir * run * 1.4
        on_ground = self.y >= ground - 0.5
        if self.state == "alert" and on_ground and now >= self._next_hop:
            self.vy = -620.0                      # hop!
            self._next_hop = now + 0.75
            on_ground = False
        if self.state == "walk" and on_ground and ground < self.bounds.bottom():
            # standing on a window: usually turn around at its edge, sometimes hop off
            if self._floor(self.x + self.walk_dir * 24) > ground + 6:
                if self._edge_turns is None:
                    self._edge_turns = random.random() < 0.75
                if self._edge_turns:
                    self.walk_dir = -self.walk_dir
                    target_vx = self.walk_dir * walk
            else:
                self._edge_turns = None
        if on_ground:
            self.vx += (target_vx - self.vx) * min(1.0, dt * 8)
        if abs(self.vx) > 5:
            self.facing = 1 if self.vx > 0 else -1

        self.vy += GRAVITY * dt
        self.x += self.vx * dt
        self.y += self.vy * dt

        if self.x < left:
            self.x, self.vx = left, abs(self.vx) * 0.6
            self.walk_dir = 1
        elif self.x > right:
            self.x, self.vx = right, -abs(self.vx) * 0.6
            self.walk_dir = -1

        if self.y >= ground:
            self.y = float(ground)
            if self.vy > 400:
                self.vy = -self.vy * 0.35   # small bounce after a fall/throw
                self.vx *= 0.8
            else:
                self.vy = 0.0
                if self.state == "fall":
                    self._set_state("idle", 1.0)
                if self._nap_after_landing:
                    self._set_state("sleep", self._nap_after_landing)
                    self._nap_after_landing = 0.0
        elif self.vy > 0 and self.state not in ("fall", "scared", "alert"):
            self.state = "fall"

        self.phase += dt * (10 if self.state in ("chase", "scared", "fetch") else 6 if self.state == "walk" else 2)
        self._apply_geometry()
        self.update()

    def _apply_geometry(self):
        self.move(int(self.x - self.S / 2), int(self.y - self.S))
        self.bubble.follow(self.geometry())

    # ---------- input ----------
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._press_pos = e.globalPosition()
            self._moved = False
            self._drag_offset = e.globalPosition() - QPointF(self.x, self.y)
            self._drag_history.clear()
            self._set_state("drag")
            self.vx = self.vy = 0.0

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.talk()

    def mouseMoveEvent(self, e):
        if self.state != "drag":
            return
        g = e.globalPosition()
        if math.hypot(g.x() - self._press_pos.x(), g.y() - self._press_pos.y()) > 4:
            self._moved = True
        self.x = g.x() - self._drag_offset.x()
        self.y = g.y() - self._drag_offset.y()
        self._drag_history.append((time.monotonic(), self.x, self.y))
        self._drag_history = self._drag_history[-6:]
        self._apply_geometry()

    def mouseReleaseEvent(self, e):
        if e.button() != Qt.MouseButton.LeftButton or self.state != "drag":
            return
        if not self._moved:
            self.hearts_until = time.monotonic() + 1.8   # a click is a pet
            self.ctrl.needs.pet()
            self._set_state("idle", 2.0)
            return
        if len(self._drag_history) >= 2:
            t0, x0, y0 = self._drag_history[0]
            t1, x1, y1 = self._drag_history[-1]
            if t1 - t0 > 1e-3:
                self.vx = max(-2500, min(2500, (x1 - x0) / (t1 - t0)))
                self.vy = max(-2500, min(2500, (y1 - y0) / (t1 - t0)))
        self._set_state("fall")

    def contextMenuEvent(self, e):
        self.ctrl.build_menu(self).exec(e.globalPos())

    # ---------- drawing ----------
    def paintEvent(self, _):
        s = self.store.s
        now = time.monotonic()
        cur = self.mapFromGlobal(QCursor.pos())
        k = BASE / self.S
        view = View(state=self.state, mood=self.mood, facing=self.facing, phase=self.phase, now=now,
                    hearts=now < self.hearts_until, cursor=QPointF(cur.x() * k, cur.y() * k),
                    color=QColor(s.color), accessory=s.accessory,
                    label=self.alert_label if self.state == "alert" else "")
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.scale(self.S / BASE, self.S / BASE)
        self.renderer.paint(p, view)
        p.end()
