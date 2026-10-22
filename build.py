"""Build a standalone executable for the OS you run this on.

    python build.py

Windows -> dist/SystemPet.exe,  Linux -> dist/SystemPet.
PyInstaller cannot cross-compile, so build on each OS (or use the GitHub Actions workflow).
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def run(*cmd):
    print("+", " ".join(map(str, cmd)))
    subprocess.run(cmd, check=True, cwd=ROOT)


def main() -> int:
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("PyInstaller is missing: pip install pyinstaller")
        return 1
    if not (ROOT / "assets" / "icon.ico").exists():
        run(sys.executable, "tools/make_icon.py")
    run(sys.executable, "-m", "PyInstaller", "packaging/system-pet.spec", "--noconfirm", "--clean",
        "--distpath", "dist", "--workpath", "build")
    exe = ROOT / "dist" / ("SystemPet.exe" if sys.platform == "win32" else "SystemPet")
    print("\nBuilt:", exe)
    return 0


if __name__ == "__main__":
    sys.exit(main())
