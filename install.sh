#!/usr/bin/env bash
# Installs Shiftly for the current user and starts it on every login.
set -euo pipefail

src="$(cd "$(dirname "$0")" && pwd)/shiftly.py"
bin_dir="$HOME/.local/bin"
autostart_dir="$HOME/.config/autostart"
apps_dir="$HOME/.local/share/applications"

mkdir -p "$bin_dir" "$autostart_dir" "$apps_dir"
install -m 755 "$src" "$bin_dir/shiftly"

desktop="[Desktop Entry]
Type=Application
Name=Shiftly
Comment=Reminds you to switch between sitting and standing
Exec=$bin_dir/shiftly
Icon=preferences-system-time
Terminal=false
Categories=Utility;
X-GNOME-Autostart-enabled=true"

echo "$desktop" > "$autostart_dir/shiftly.desktop"
echo "$desktop" > "$apps_dir/shiftly.desktop"

echo "Installed to $bin_dir/shiftly; it will start on next login."
echo "Start it now with: shiftly &"
