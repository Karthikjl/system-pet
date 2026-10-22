import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest


@pytest.fixture(autouse=True)
def isolated_dirs(tmp_path, monkeypatch):
    """Every test gets its own config/data folders, so the real settings are never touched."""
    monkeypatch.setenv("SYSTEM_PET_CONFIG_DIR", str(tmp_path / "cfg"))
    monkeypatch.setenv("SYSTEM_PET_DATA_DIR", str(tmp_path / "data"))


@pytest.fixture(scope="session")
def qapp():
    from PyQt6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])
