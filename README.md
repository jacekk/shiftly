# Shiftly

A tiny Linux tray app that cycles through named phases (e.g. *Sitting 40 min → Standing 20 min*) and sends a notification when it's time to change position.

- Per-phase names and durations, all editable in a settings window
- Tray icon shows the current phase and time left
- Pause / resume, skip to next phase, or start any phase directly
- Starts on login

Built for Linux Mint (Cinnamon); falls back to a plain GTK status icon elsewhere.

## Install

Requires Python 3, GTK 3, `gir1.2-notify-0.7` (all present on Mint by default).

```
./install.sh
shiftly &
```

Config lives in `~/.config/shiftly/config.json`. Running `shiftly` again opens the settings of the running instance.
