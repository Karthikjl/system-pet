# System Pet

A customizable desktop pet for **Windows and Linux** (Python + PyQt6). It lives on top of your screen,
reacts to your mouse, and reacts to your system.

## Install / run

### From source (any OS)
```bash
pip install -r requirements.txt
python main.py
```
Open **Settings** by clicking the tray icon, or from the pet's right-click menu.

### As a standalone app
PyInstaller can't cross-compile, so build on the OS you want the app for:
```bash
pip install -r requirements-build.txt
python build.py
```
| OS | Output | Notes |
|---|---|---|
| Windows | `dist\SystemPet.exe` | Double-click to run. No console window. |
| Linux | `dist/SystemPet` | Run `packaging/install-linux.sh` to add it to your app menu. |

Or push the project to GitHub: the workflow in `.github/workflows/build.yml` builds both and
uploads them as downloadable artifacts.

Linux runtime needs the Qt xcb libraries (Debian/Ubuntu/Kali: `sudo apt install libxcb-cursor0 libegl1 libxkbcommon-x11-0`).

`python main.py --check` prints the platform, config folders and skins found. Include it in bug reports.

## What it does
- **Moves:** falls with gravity, wanders, naps, chases your cursor, gets scared by fast mouse swipes.
  A napping pet stays asleep until the nap ends; only a click, a drag, a fast mouse swipe, a reminder,
  or food/ball wakes it.
- **Interaction:** click to pet, drag to carry, release while moving to throw, double-click to chat.
  Right-click or use the tray to **feed a fish**, **play ball**, nap, or chat.
- **Needs:** fullness, energy and happiness decay over time and are saved between runs.
- **System mood:** hot (CPU > 80%), sick (RAM > 90%), hungry (low battery or low fullness), sad (low happiness).
  It speaks up in a bubble when something is wrong.
- **Reminders:** water, 20-20-20 eye rest, Pomodoro (see below).
- **Autostart:** optional, from Settings > System (XDG autostart on Linux, Run registry key on Windows).
- Only one copy runs at a time.

## Reminders
When a reminder fires you get three things, so it is hard to miss:
1. A **pop-up card** slides in at the top-right of the screen (coloured icon, message, 14 seconds; click to dismiss).
2. The **pet wakes up and hops** with wide eyes and "!" marks, with a speech bubble.
3. An optional **desktop notification** (needs the tray icon; turn it off in Settings > Reminders).

Defaults: water every 45 min, eye rest every 20 min, Pomodoro off (25 min work / 5 min break).
Use the **Preview** buttons in Settings > Reminders to see how each one looks, or set an interval to 1 minute
to wait for a real one.

## Customization (Settings window, applies live)
- Name, size, speed, number of pets (1-5)
- Drawn cat: colour and accessory (bow, party hat, glasses)
- Skins: pick a sprite-sheet skin from the dropdown
- Toggle chasing, napping, scaring; set reminder intervals

| | Linux | Windows |
|---|---|---|
| Settings | `~/.config/system-pet/config.json` | `%APPDATA%\SystemPet\config.json` |
| Pet needs | `~/.local/share/system-pet/state.json` | `%LOCALAPPDATA%\SystemPet\state.json` |
| Your skins | `~/.config/system-pet/skins/<name>/` | `%APPDATA%\SystemPet\skins\<name>\` |

## Making a skin
Create a folder `<name>` in your skins location (or `skins/<name>/` in this project) with:
```json
{
  "name": "My Skin",
  "fps": 8,
  "frames": {
    "idle": ["idle_0.png", "idle_1.png"],
    "walk": ["walk_0.png", "walk_1.png", "walk_2.png", "walk_3.png"],
    "sleep": ["sleep_0.png"]
  }
}
```
Frames are square PNGs (240x240 recommended) of the pet **facing right**, feet at the bottom edge.
Only `idle` is required. Other states: `walk`, `sleep`, `scared`, `drag`, `fall`; anything missing
falls back (walk for chase/fetch, idle for the rest). Then click **Reload skins** in Settings.
`tools/make_skins.py` generates the two bundled skins and is a good template.

## Platform notes
- **Wayland (Linux):** Wayland blocks apps from positioning windows and reading the global cursor, so
  the app forces Qt's `xcb` (XWayland) backend. Cursor tracking may only work while the pointer is over
  XWayland windows; an X11 session works best.
- **Windows:** the Windows build has not been tested by the author yet; please report problems.
- **Build error `No module named 'distutils'`:** an old `packaging` package in `~/.local` shadows the
  system one on Python 3.13. Build with `PYTHONNOUSERSITE=1 python3 build.py`, or `pip install -U packaging`.

## Development
- `python main.py --check` prints the platform, folders and skins found (handy for bug reports).
- `python tools/make_skins.py` regenerates the bundled skins; `python tools/make_icon.py` regenerates the icon.
- Offscreen runs for testing: `QT_QPA_PLATFORM=offscreen python main.py` with `SYSTEM_PET_CONFIG_DIR` and
  `SYSTEM_PET_DATA_DIR` pointing at a scratch folder so your real settings are untouched.

## Layout
- `main.py`: entry point (`--check` for diagnostics); `build.py`: build the app
- `system_pet/app.py`: controller (pets, tray, menus, settings window)
- `system_pet/pet.py`: window, physics, behaviour
- `system_pet/render/`: drawn cat and sprite-skin renderers
- `system_pet/paths.py`: per-OS folders; `autostart.py`: per-OS start-on-login
- `system_pet/config.py`, `needs.py`, `reminders.py`, `stats.py`, `bubble.py`, `toast.py`, `items.py`
- `system_pet/ui/`: settings window and tray icon
- `skins/`, `assets/`: bundled skins and icon; `packaging/`: PyInstaller spec and Linux installer
