# Skin template

A skin is a folder with a `skin.json` and PNG frames. Copy this folder, draw your frames, then validate:

```bash
python tools/validate_skin.py path/to/your-skin
```

## Rules
- Square PNGs with a transparent background, the **same size** for every frame (240x240 recommended; 64-1024 allowed).
- Draw the pet **facing right**, feet touching the **bottom edge** of the image. The app flips it for the other direction.
- Only `idle` is required. Optional states: `walk`, `sleep`, `scared`, `alert`, `drag`, `fall`, `eat`, `chase`, `fetch`.
  Missing states fall back (`chase`/`fetch` use `walk`, everything else uses `idle`).
- Each frame under 1 MB, whole skin under 5 MB, `fps` between 1 and 30.
- The app adds the "zzz", hearts and "!" decorations itself, so do not draw them into your frames.
- Add `author` and `license` to `skin.json`. Only submit art you made or have the right to share under an
  MIT-compatible license.

`guide.png` is a transparent canvas with the foot line and facing direction marked: paint over it, then delete the guide layer.

## Try it
Put the folder in `~/.config/system-pet/skins/` (Linux) or `%APPDATA%\SystemPet\skins\` (Windows), open
**Settings > Appearance** and press **Reload skins**.
