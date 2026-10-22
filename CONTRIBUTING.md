# Contributing to System Pet

Thanks for helping! Bug reports, skins, and code are all welcome.

## Report a bug
Open an issue and paste the output of `python main.py --check` (it prints your OS, session type, folders and
skins). Say what you expected and what happened.

## Set up
```bash
git clone https://github.com/Karthikjl/system-pet.git
cd system-pet
pip install -r requirements.txt -r requirements-dev.txt
python main.py                 # run the app
python -m pytest               # run the tests (offscreen, no display needed)
```
Windows and Linux are both supported. On Wayland, run via XWayland (the app does this for you).

## Add a skin
1. Copy `docs/skin-template/` and read its README (size, facing direction, states, limits).
2. Draw your frames, fill in `skin.json` (`name`, `author`, `license`, `fps`, `frames`).
3. Validate it: `python tools/validate_skin.py path/to/your-skin`
4. Put the folder in `skins/<your-skin>/`, then run `python tools/make_gallery.py` to add it to the README gallery.
5. Open a pull request. Only submit art you made or may share under an MIT-compatible license.

CI runs the same validator on every skin in `skins/`.

## Change the code
- Keep changes small and focused; match the style of the surrounding code (short docstrings, no unneeded abstractions).
- Add or update a test in `tests/` for logic changes (pure functions are the easiest to test; see `tests/test_guard.py`).
- Anything platform-specific goes behind `sys.platform` checks and must not break the other OS.
- If you change visuals, regenerate the README images: `python tools/make_demo.py`.
- Commit messages: a short imperative subject, then a sentence or two on why.

## Ideas that would be welcome
More skins, window-walking improvements on Windows, translations, and new pet behaviours. Open an issue first
for anything big so we can agree on the approach.
