#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
INDEX_URL="https://raw.githubusercontent.com/MurderFromMars/HandheldStreamingServiceUtility/main/data/links.index"
INDEX_FILE="${XDG_CACHE_HOME:-$HOME/.cache}/pi-phone-streaming-links.index"

command -v chromium >/dev/null 2>&1 || { echo "Chromium is not installed."; exit 1; }
command -v zenity >/dev/null 2>&1 || { echo "Zenity is not installed."; exit 1; }
mkdir -p "$APP_DIR" "$(dirname "$INDEX_FILE")"
curl -fL "$INDEX_URL" -o "$INDEX_FILE"

mapfile -t services < <(sed '/^#/d;/^$/d;s/|.*//' "$INDEX_FILE")
choices=()
for service in "${services[@]}"; do
    choices+=(FALSE "$service")
done

selected="$(zenity --list --checklist --separator='|' --title='Pi Phone streaming apps' --text='Choose web apps to add to your application menu.' --column='Install' --column='Service' --width=520 --height=650 "${choices[@]}")" || exit 0

IFS='|' read -r -a selected_services <<< "$selected"
for service in "${selected_services[@]}"; do
    line="$(grep -E "^$(printf '%s' "$service" | sed 's/[][\\.^$*+?(){}|]/\\&/g')\\|" "$INDEX_FILE" | head -n 1 || true)"
    [ -n "$line" ] || continue
    url="${line#*|}"
    url="${url%%|*}"
    safe_name="$(printf '%s' "$service" | tr ' /' '__' | tr -cd '[:alnum:]_.-')"
    desktop_file="$APP_DIR/pi-phone-${safe_name}.desktop"
    cat > "$desktop_file" <<DESKTOP
[Desktop Entry]
Name=$service
Type=Application
Exec=chromium --app=$url --start-maximized
Terminal=false
Categories=Network;AudioVideo;
DESKTOP
    chmod 0644 "$desktop_file"
done

echo "Streaming web apps were added to $APP_DIR"