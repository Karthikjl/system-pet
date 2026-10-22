#!/usr/bin/env bash
# Installs the built binary for the current user: launcher in the app menu + ~/.local/bin/system-pet
set -euo pipefail
here="$(cd "$(dirname "$0")/.." && pwd)"
bin="$here/dist/SystemPet"
[ -x "$bin" ] || { echo "Build first: python3 build.py"; exit 1; }

install -Dm755 "$bin" "$HOME/.local/bin/system-pet"
install -Dm644 "$here/assets/icon.png" "$HOME/.local/share/icons/hicolor/256x256/apps/system-pet.png"
mkdir -p "$HOME/.local/share/applications"
cat > "$HOME/.local/share/applications/system-pet.desktop" <<DESK
[Desktop Entry]
Type=Application
Name=System Pet
Comment=A customizable desktop pet
Exec=$HOME/.local/bin/system-pet
Icon=system-pet
Categories=Game;Utility;
Terminal=false
DESK
echo "Installed. Launch 'System Pet' from your app menu, or run: system-pet"
