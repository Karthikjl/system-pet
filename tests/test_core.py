import json

from system_pet.config import Settings, SettingsStore
from system_pet.needs import Needs
from system_pet.reminders import Reminders


def test_needs_decay_feed_and_clamp():
    n = Needs(fullness=50, energy=50, happiness=50)
    n.tick(60, asleep=False)
    assert n.fullness < 50 and n.energy < 50 and n.happiness < 50
    n.feed()
    n.feed()
    n.feed()
    assert n.fullness == 100          # clamped


def test_needs_asleep_restores_energy():
    n = Needs(energy=40)
    n.tick(30, asleep=True)
    assert n.energy > 40


def test_mood_priority():
    assert Needs(fullness=10).mood("happy") == "hungry"
    assert Needs(happiness=10).mood("happy") == "sad"
    assert Needs(fullness=10).mood("hot") == "hot"      # system trouble wins
    assert Needs().mood("happy") == "happy"


def test_needs_save_load_never_starts_in_bad_shape(monkeypatch):
    import system_pet.needs as needs
    Needs(fullness=90, energy=90, happiness=90).save()
    raw = json.loads(Needs._path().read_text())
    raw["saved_at"] -= 3600 * 48                      # closed for two days
    Needs._path().write_text(json.dumps(raw))
    loaded = Needs.load()
    assert loaded.fullness >= 35 and loaded.happiness >= 35
    assert needs.FULLNESS_RATE > 0


def test_settings_roundtrip_and_bad_values(qapp):
    store = SettingsStore()
    store.update(name="Rex", size=150, guard_enabled=True)
    again = SettingsStore()
    assert (again.s.name, again.s.size, again.s.guard_enabled) == ("Rex", 150, True)
    store.path.write_text(json.dumps({"size": "huge", "speed": "2.5", "unknown": 1}))
    broken = SettingsStore()
    assert broken.s.size == Settings().size           # unusable value falls back to the default
    assert broken.s.speed == 2.5                      # convertible value is accepted


def test_reminders_fire_on_schedule_and_pomodoro_cycles(qapp):
    store = SettingsStore()
    store.update(water_enabled=True, water_min=1, eye_enabled=False,
                 pomo_enabled=True, pomo_work=2, pomo_break=1)
    r = Reminders(store)
    r.timer.stop()
    got = []
    r.message.connect(lambda kind, text: got.append((kind, text)))
    for _ in range(190):
        r.tick()
    kinds = [k for k, _ in got]
    assert kinds.count("water") == 3
    assert "pomo_break" in kinds and "pomo_work" in kinds
    assert kinds.index("pomo_break") < kinds.index("pomo_work")


def test_unrelated_setting_change_does_not_reset_reminder_timer(qapp):
    store = SettingsStore()
    r = Reminders(store)
    r.timer.stop()
    r.water_left = 123
    store.update(size=140)
    assert r.water_left == 123
    store.update(water_min=7)
    assert r.water_left == 7 * 60
