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

cat > /usr/local/bin/pi-phone-update <<'UPDATE'
#!/usr/bin/env bash
set -euo pipefail
tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT
curl -fL https://github.com/Amiriscoo/rpi-phone-system/archive/refs/heads/main.tar.gz | tar -xz -C "$tmp_dir"
new_client="$tmp_dir/rpi-phone-system-main/client"
config_backup="$(mktemp)"
cp /opt/rpi-phone/client/config/client.json "$config_backup"
rm -rf /opt/rpi-phone/client/main.py /opt/rpi-phone/client/networking /opt/rpi-phone/client/audio
cp -a "$new_client/." /opt/rpi-phone/client/
cp "$config_backup" /opt/rpi-phone/client/config/client.json
rm -f "$config_backup"
chown -R pi:pi /opt/rpi-phone/client
systemctl restart rpi-phone-client.service
UPDATE
chmod 755 /usr/local/bin/pi-phone-update