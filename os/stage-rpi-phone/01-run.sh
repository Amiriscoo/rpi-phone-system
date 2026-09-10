#!/usr/bin/env bash
set -euo pipefail

install -d -o pi -g pi /opt/rpi-phone/client/config
python3 -m venv --system-site-packages /opt/rpi-phone/client/.venv
chown -R pi:pi /opt/rpi-phone/client

sed -i 's#^  "server_url".*#  "server_url": "https://configure-this-tailnet-url",#' /opt/rpi-phone/client/config/client.json

cat > /etc/systemd/system/rpi-phone-client.service <<'SERVICE'
[Unit]
Description=Pi Phone touchscreen and desktop client
After=graphical.target NetworkManager.service
Wants=NetworkManager.service

[Service]
Type=simple
User=pi
WorkingDirectory=/opt/rpi-phone/client
Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/pi/.Xauthority
ExecStart=/opt/rpi-phone/client/.venv/bin/python /opt/rpi-phone/client/main.py
Restart=always
RestartSec=3
NoNewPrivileges=true

[Install]
WantedBy=graphical.target
SERVICE

ln -sf /etc/systemd/system/rpi-phone-client.service /etc/systemd/system/graphical.target.wants/rpi-phone-client.service
systemctl enable NetworkManager.service || true