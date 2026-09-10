#!/usr/bin/env bash
set -euo pipefail

INSTALL_ROOT="/opt/rpi-phone/client"
SERVICE_NAME="rpi-phone-client"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLIENT_SOURCE="$(cd "$SCRIPT_DIR/.." && pwd)"
PI_USER="${SUDO_USER:-${USER}}"

if [[ "$(id -u)" -ne 0 ]]; then
    echo "Run this installer with sudo: sudo ./scripts/install_raspberry_pi.sh"
    exit 1
fi

if ! id "$PI_USER" >/dev/null 2>&1; then
    echo "User '$PI_USER' does not exist. Run this from the Pi's normal desktop account."
    exit 1
fi

read -r -p "Tailscale Serve HTTPS URL (for example https://phone.example.ts.net): " SERVER_URL
if [[ ! "$SERVER_URL" =~ ^https:// ]]; then
    echo "The server URL must use HTTPS through Tailscale Serve."
    exit 1
fi

apt-get update
apt-get install -y python3-venv python3-pyside6 network-manager curl
systemctl enable --now NetworkManager

install -d -o "$PI_USER" -g "$PI_USER" "$INSTALL_ROOT/config"
cp -a "$CLIENT_SOURCE/." "$INSTALL_ROOT/"
chown -R "$PI_USER:$PI_USER" "$INSTALL_ROOT"

python3 -m venv --system-site-packages "$INSTALL_ROOT/.venv"
sed -i "s#^  \"server_url\".*#  \"server_url\": \"$SERVER_URL\",#" "$INSTALL_ROOT/config/client.json"
chown -R "$PI_USER:$PI_USER" "$INSTALL_ROOT"

cat > "/etc/systemd/system/$SERVICE_NAME.service" <<SERVICE
[Unit]
Description=Pi Phone touchscreen client
After=graphical.target NetworkManager.service
Wants=NetworkManager.service

[Service]
Type=simple
User=$PI_USER
WorkingDirectory=$INSTALL_ROOT
Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/$PI_USER/.Xauthority
ExecStart=$INSTALL_ROOT/.venv/bin/python $INSTALL_ROOT/main.py
Restart=always
RestartSec=3
NoNewPrivileges=true

[Install]
WantedBy=graphical.target
SERVICE

systemctl daemon-reload
systemctl enable "$SERVICE_NAME.service"
echo
echo "Installation complete."
echo "Connect Wi-Fi, install Tailscale, then run: sudo tailscale up"
echo "Start the client with: sudo systemctl start $SERVICE_NAME"