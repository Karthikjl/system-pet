"""Rebuild the skin gallery table in README.md from skins/*/skin.json.

    python tools/make_gallery.py
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
START, END = "<!-- skins:start -->", "<!-- skins:end -->"


def table() -> str:
    rows = ["| Preview | Skin | Author | License |", "|---|---|---|---|"]
    for folder in sorted(p for p in (ROOT / "skins").iterdir() if (p / "skin.json").is_file()):
        meta = json.loads((folder / "skin.json").read_text())
        idle = meta["frames"]["idle"][0]
        rows.append(f'| <img src="skins/{folder.name}/{idle}" width="64"> | {meta.get("name", folder.name)} '
                    f'(`{folder.name}`) | {meta.get("author", "unknown")} | {meta.get("license", "unknown")} |')
    return "\n".join(rows)


def main() -> int:
    readme = ROOT / "README.md"
    text = readme.read_text()
    block = f"{START}\n{table()}\n{END}"
    new, n = re.subn(re.escape(START) + r".*?" + re.escape(END), lambda _: block, text, flags=re.S)
    if n != 1:
        print(f"README.md needs exactly one {START} ... {END} block")
        return 1
    readme.write_text(new)
    print("gallery updated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
