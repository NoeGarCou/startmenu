#!/usr/bin/env bash
# Launcher wrapper for StartMenu.
# Can be invoked from any working directory (e.g. a Plank .desktop or a
# Cinnamon keyboard shortcut) — it always cd's to its own directory first.
cd "$(dirname "$(realpath "$0")")"
exec python3 -m startmenu "$@"
