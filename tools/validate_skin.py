"""Check sprite skin folders before submitting them.

    python tools/validate_skin.py skins/ghost ~/.config/system-pet/skins/mine
    python tools/validate_skin.py --all          # every folder in ./skins
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PyQt6.QtGui import QImage

from system_pet.render.sprite import KNOWN_STATES

MAX_FILE = 1 * 1024 * 1024
MAX_TOTAL = 5 * 1024 * 1024
MIN_PX, MAX_PX = 64, 1024


def validate(folder: Path) -> tuple[list[str], list[str]]:
    """Return (errors, warnings). A skin with no errors will load in the app."""
    errors, warnings = [], []
    meta = folder / "skin.json"
    if not meta.is_file():
        return [f"{folder.name}: skin.json is missing"], warnings
    try:
        data = json.loads(meta.read_text())
    except ValueError as e:
        return [f"skin.json is not valid JSON: {e}"], warnings
    if not isinstance(data, dict):
        return ["skin.json must contain a JSON object"], warnings

    if not isinstance(data.get("name"), str) or not data["name"].strip():
        errors.append('"name" must be a non-empty string')
    fps = data.get("fps", 8)
    if isinstance(fps, bool) or not isinstance(fps, (int, float)) or not 1 <= fps <= 30:
        errors.append('"fps" must be a number between 1 and 30')
    for key in ("author", "license"):
        if key in data and not isinstance(data[key], str):
            errors.append(f'"{key}" must be a string')
    if "author" not in data or "license" not in data:
        warnings.append('add "author" and "license" so the skin can be credited in the gallery')

    frames = data.get("frames")
    if not isinstance(frames, dict) or not frames:
        return errors + ['"frames" must map state names to lists of PNG files'], warnings
    if "idle" not in frames:
        errors.append('"frames" must include "idle" (every other state falls back to it)')
    if "walk" not in frames:
        warnings.append('no "walk" frames: the pet will slide while walking')

    total, sizes = 0, set()
    for state, files in frames.items():
        if state not in KNOWN_STATES:
            errors.append(f'unknown state "{state}" (known: {", ".join(sorted(KNOWN_STATES))})')
        if not isinstance(files, list) or not files or not all(isinstance(f, str) for f in files):
            errors.append(f'"{state}" must be a non-empty list of file names')
            continue
        for name in files:
            path = (folder / name).resolve()
            if folder.resolve() not in path.parents:
                errors.append(f'{name}: files must be inside the skin folder')
                continue
            if path.suffix.lower() != ".png":
                errors.append(f"{name}: only .png files are supported")
            if not path.is_file():
                errors.append(f"{name}: file not found")
                continue
            size = path.stat().st_size
            total += size
            if size > MAX_FILE:
                errors.append(f"{name}: {size / 1048576:.1f} MB is over the 1 MB per-file limit")
            img = QImage(str(path))
            if img.isNull():
                errors.append(f"{name}: not a readable image")
                continue
            if img.width() != img.height():
                errors.append(f"{name}: must be square, found {img.width()}x{img.height()}")
            if not MIN_PX <= img.width() <= MAX_PX:
                errors.append(f"{name}: width must be {MIN_PX}-{MAX_PX}px, found {img.width()}")
            sizes.add((img.width(), img.height()))
    if len(sizes) > 1:
        errors.append("all frames must have the same size, found: "
                      + ", ".join(f"{w}x{h}" for w, h in sorted(sizes)))
    if total > MAX_TOTAL:
        errors.append(f"skin is {total / 1048576:.1f} MB, over the 5 MB limit")
    return errors, warnings


def main(argv: list[str]) -> int:
    if argv == ["--all"]:
        folders = sorted(p for p in (ROOT / "skins").iterdir() if p.is_dir())
    else:
        folders = [Path(a) for a in argv]
    if not folders:
        print(__doc__)
        return 2
    failed = False
    for folder in folders:
        errors, warnings = validate(folder)
        print(("FAIL " if errors else "ok   ") + folder.name)
        for line in errors:
            print("   error:  ", line)
        for line in warnings:
            print("   warning:", line)
        failed = failed or bool(errors)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
