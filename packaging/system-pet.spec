# PyInstaller spec: builds a single windowed executable for the current OS.
#   Windows -> dist/SystemPet.exe        Linux -> dist/SystemPet
import sys
from pathlib import Path

root = Path(SPECPATH).parent
icon = str(root / "assets" / "icon.ico") if sys.platform == "win32" else None

a = Analysis(
    [str(root / "main.py")],
    pathex=[str(root)],
    datas=[(str(root / "skins"), "skins"), (str(root / "assets"), "assets")],
    excludes=["tkinter"],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name="SystemPet",
    console=False,          # no terminal window on Windows
    icon=icon,
    upx=False,
)
