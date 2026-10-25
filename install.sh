#!/usr/bin/env bash
# Installs Shiftly for the current user and starts it on every login.
set -euo pipefail

src="$(cd "$(dirname "$0")" && pwd)/shiftly.py"
bin_dir="$HOME/.local/bin"
autostart_dir="$HOME/.config/autostart"
apps_dir="$HOME/.local/share/applications"
icons_dir="$HOME/.local/share/icons/hicolor"

mkdir -p "$bin_dir" "$autostart_dir" "$apps_dir"
install -m 755 "$src" "$bin_dir/shiftly"

icons_src="$(dirname "$src")/icons"
mkdir -p "$icons_dir/scalable/apps" "$icons_dir/symbolic/apps"
install -m 644 "$icons_src/shiftly.svg" "$icons_dir/scalable/apps/shiftly.svg"
install -m 644 "$icons_src/shiftly-symbolic.svg" "$icons_dir/symbolic/apps/shiftly-symbolic.svg"
gtk-update-icon-cache -q -t "$icons_dir" 2>/dev/null || true

desktop="[Desktop Entry]
Type=Application
Name=Shiftly
Comment=Reminds you to switch between sitting and standing
Exec=$bin_dir/shiftly
Icon=shiftly
Terminal=false
Categories=Utility;
X-GNOME-Autostart-enabled=true"

echo "$desktop" > "$autostart_dir/shiftly.desktop"
echo "$desktop" > "$apps_dir/shiftly.desktop"

echo "Installed to $bin_dir/shiftly; it will start on next login."
echo "Start it now with: shiftly &"
