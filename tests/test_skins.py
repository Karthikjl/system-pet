import json
import shutil
from pathlib import Path

import pytest
from PyQt6.QtGui import QImage

from tools.validate_skin import validate

SKINS = Path(__file__).resolve().parents[1] / "skins"


@pytest.mark.parametrize("folder", sorted(p for p in SKINS.iterdir() if p.is_dir()), ids=lambda p: p.name)
def test_bundled_skins_are_valid(folder):
    errors, _ = validate(folder)
    assert errors == []


@pytest.fixture
def skin(tmp_path):
    dest = tmp_path / "skin"
    shutil.copytree(SKINS / "ghost", dest)
    return dest


def edit(skin, fn):
    meta = skin / "skin.json"
    data = json.loads(meta.read_text())
    fn(data)
    meta.write_text(json.dumps(data))


def errors_of(skin):
    return " | ".join(validate(skin)[0])


def test_missing_frame_file(skin):
    (skin / "idle_0.png").unlink()
    assert "idle_0.png: file not found" in errors_of(skin)


def test_missing_idle_state(skin):
    edit(skin, lambda d: d["frames"].pop("idle"))
    assert '"idle"' in errors_of(skin)


def test_bad_fps_and_unknown_state(skin):
    def mutate(d):
        d["fps"] = 99
        d["frames"]["dance"] = ["idle_0.png"]
    edit(skin, mutate)
    out = errors_of(skin)
    assert '"fps"' in out and 'unknown state "dance"' in out


def test_non_square_and_mixed_sizes(skin):
    QImage(200, 100, QImage.Format.Format_ARGB32).save(str(skin / "idle_1.png"))
    out = errors_of(skin)
    assert "must be square" in out and "same size" in out


def test_path_escape_is_rejected(skin):
    edit(skin, lambda d: d["frames"].update(idle=["../skin.json"]))
    assert "inside the skin folder" in errors_of(skin)


def test_invalid_json(skin):
    (skin / "skin.json").write_text("{not json")
    assert "not valid JSON" in errors_of(skin)
