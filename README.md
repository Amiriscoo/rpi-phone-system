# Pi Phone: Wi-Fi-only Raspberry Pi smartphone

## Architecture

```text
Raspberry Pi touchscreen
  | Wi-Fi (home, hotspot, or public Internet)
  v
Tailscale encrypted private network
  v
Linux VM on Windows PC (FastAPI + SQLite)
  | REST/WebSocket messaging, contacts, devices, presence
  v
Optional SIP/WebRTC service and optional PSTN provider
```

This project is intentionally Wi-Fi-only. Wi-Fi does not provide a cellular number. The included system supports authenticated users, messaging, contacts, device registration, presence-ready WebSocket notifications, local/offline UI, and a call screen. Audio calls need a media service: use WebRTC (recommended for device-to-device calls) or a SIP client/server. Phone-number calling additionally needs a SIP trunk/PSTN provider and costs may apply.

The image includes Chromium and Bluetooth tools. YouTube, TikTok, and Netflix open as web services; DRM, performance, and account support depend on the service and Pi model. APK files are Android packages and do not run natively on Raspberry Pi OS. Roblox does not have a supported native ARM Linux client. Linux applications can be installed through Raspberry Pi OS packages or Pi-Apps. The Apps screen can update the Pi Phone client from GitHub while connected to the Internet; PC-managed updates can also be run over SSH/Tailscale with `sudo /usr/local/bin/pi-phone-update`.

## Build A Flashable OS

Anyone can build a clean Pi Phone OS image from this repository. The builder asks each person for their own Pi password and does not include Wi-Fi credentials, Tailscale keys, server secrets, or account sessions.

On Ubuntu, Debian, or WSL2:

```bash
git clone https://github.com/Amiriscoo/rpi-phone-system.git
cd rpi-phone-system
bash install.sh
```

On Windows PowerShell:

```powershell
git clone https://github.com/Amiriscoo/rpi-phone-system.git
cd rpi-phone-system
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

The Windows installer uses WSL2 automatically. The generated image appears in `os/images`. Flash it with Raspberry Pi Imager, boot the Pi, configure Wi-Fi, set the server URL, and run `sudo tailscale up`. See [os/README.md](os/README.md) for hardware and first-boot details.

## Technology choices

- **Client:** PySide6/Qt gives a modern hardware-accelerated touch UI and works well on Pi 4/5. Pi Zero 2 W can run it with a lightweight Qt image, but Pi 4 is recommended for smooth animations.
- **Backend:** FastAPI, SQLite, Python standard-library `scrypt` password hashing, PyJWT, and WebSockets. It is small enough for a home VM and easy to inspect.
- **Remote access:** Tailscale is WireGuard-based and avoids exposing the API or SSH to the public Internet. The API binds to localhost; Tailscale provides the private path.

## Project layout

`server/backend` contains the API and database setup. `server/database` stores the SQLite database. `server/config` stores secrets outside source control. `client/main.py` contains the UI, while `client/networking` contains authenticated HTTP access.

The original workspace entry `ai.py/rpi_phone` is a zero-byte file, so the runnable project is in `rpi_phone_system`; the original file was not modified.

## Linux VM setup

Use Ubuntu Server 24.04 LTS in Hyper-V or VirtualBox. Give it a fixed VM address if desired, but do not port-forward the API.

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-venv python3-pip git ufw curl
sudo useradd --system --create-home --home /opt/rpi-phone rpiphone
sudo mkdir -p /opt/rpi-phone
sudo chown -R "$USER":"$USER" /opt/rpi-phone
# Copy this rpi_phone_system/server directory to /opt/rpi-phone/server
cd /opt/rpi-phone/server
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp config/server.env.example config/server.env
openssl rand -hex 32
nano config/server.env
```

Put the generated value after `RPI_PHONE_JWT_SECRET=`. Then install the service:

```bash
sudo chown -R rpiphone:rpiphone /opt/rpi-phone
sudo cp systemd/rpi-phone.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now rpi-phone
curl http://127.0.0.1:8787/health
```

## Tailscale VPN

Install Tailscale on both the VM and Pi from https://tailscale.com/download/linux, then run:

```bash
sudo tailscale up
tailscale ip -4
```

Use the VM's `100.x.y.z` Tailscale address in `client/config/client.json`. Keep the API bound to `127.0.0.1` if you use a Tailscale sidecar/reverse proxy, or bind it to the VM's Tailscale IP only and restrict access with the firewall. Do not port-forward 8787 or SSH on the home router.

The simplest private setup is to run a Tailscale Serve HTTPS proxy on the VM:

```bash
sudo tailscale serve --https=443 http://127.0.0.1:8787
tailscale serve status
```

Set the client `server_url` to the HTTPS URL shown by Tailscale Serve. This gives TLS plus the private VPN path.

## Firewall

The API should be reachable only through Tailscale Serve. On the VM:

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow in on tailscale0 to any port 443 proto tcp
sudo ufw enable
sudo ufw status verbose
```

Do not add a public WAN rule for port 8787. If you need SSH, use `sudo ufw allow in on tailscale0 to any port 22 proto tcp`, not a router port-forward.

## Raspberry Pi OS setup

Use Raspberry Pi OS Bookworm 64-bit. Pi 4/5 is recommended; Pi Zero 2 W is viable with fewer animations and no heavy AI inference.

```bash
sudo apt update
sudo apt install -y python3-venv python3-pyside6 network-manager
sudo systemctl enable --now NetworkManager
mkdir -p /opt/rpi-phone/client
# Copy this client directory to /opt/rpi-phone/client
cd /opt/rpi-phone/client
python3 -m venv --system-site-packages .venv
.venv/bin/pip install -r requirements-pi.txt
nano config/client.json
```

### One-command Pi installation

The repository includes an installer for Raspberry Pi OS Bookworm. Copy the complete `client` directory to the Pi using a USB drive, `scp` over your Tailscale network, or a Git checkout. Then run:

```bash
cd client
sudo bash ./scripts/install_raspberry_pi.sh
```

The installer installs Raspberry Pi packages, copies the client to `/opt/rpi-phone/client`, creates a system Python environment, asks for the Tailscale Serve HTTPS URL, detects the logged-in desktop user, and enables the touchscreen service. It does not install PySide6 from pip because ARM builds are more reliable through Raspberry Pi OS packages.

To start or inspect the installed app:

```bash
sudo systemctl start rpi-phone-client
systemctl status rpi-phone-client
journalctl -u rpi-phone-client -f
```

## Monitor, mouse, and keyboard modes

The client is a normal Qt desktop window, so HDMI monitors, USB mice, USB keyboards, and Bluetooth input devices work without a separate build. The service starts in windowed mode. For a touchscreen-only kiosk, change the generated service command to:

```ini
ExecStart=/opt/rpi-phone/client/.venv/bin/python /opt/rpi-phone/client/main.py --fullscreen
```

Then reload it:

```bash
sudo systemctl daemon-reload
sudo systemctl restart rpi-phone-client
```

Keyboard navigation is available with `Alt+1` through `Alt+6` for the six screens and `Escape` to return home. Mouse clicks and keyboard focus work on every button and text field.

## USB OTG mode

On a Pi Zero 2 W, the single micro-USB OTG/data port can operate either as a USB gadget connected to a computer or as a USB host connected to peripherals. It cannot do both at the same time through that one port. Use Bluetooth keyboard/mouse while gadget mode is active, or disable gadget mode before using a USB hub for wired peripherals. HDMI remains available through the display connector.

Configure USB Ethernet gadget mode on Raspberry Pi OS with:

```bash
cd client
sudo bash ./scripts/configure_otg.sh
sudo reboot
```

For Pi 4 and Pi 5, use the normal USB host ports for mouse and keyboard; OTG is not needed for ordinary peripherals. The USB gadget script is intended primarily for the Zero 2 W.

This is an application installer, not a complete `.img` disk image. Flash Raspberry Pi OS with Raspberry Pi Imager first, boot the Pi, connect it to Wi-Fi, and run the installer. This gives you the customized Pi Phone OS behavior on top of Raspberry Pi OS while retaining the standard desktop, HDMI, USB, mouse, and keyboard support. A prebuilt OS image would be tied to a particular Pi model, display configuration, user account, Wi-Fi setup, and Tailscale identity, so it would be less portable and would risk shipping secrets.

For a reproducible custom `.img` image, use the [OS image build guide](os/README.md) and `os/build.sh`. It builds a Pi Phone Linux distribution with the client and startup service preinstalled.

Set `server_url` to your Tailscale Serve URL, not your home LAN address. Connect Wi-Fi with the normal Raspberry Pi UI or `nmcli`; NetworkManager remembers saved networks and automatically reconnects:

```bash
nmcli device wifi list
nmcli device wifi connect "HOTSPOT_NAME" password "HOTSPOT_PASSWORD"
```

Install Tailscale, run `sudo tailscale up`, and verify `tailscale ping <vm-name>`. Test the app with `.venv/bin/python main.py`.

## Automatic startup

On the Pi:

```bash
sudo cp systemd/rpi-phone-client.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now rpi-phone-client
journalctl -u rpi-phone-client -f
```

A desktop session must be configured to auto-login for the graphical service. On a Pi Zero 2 W, disable unnecessary desktop effects and use a 480x800 display profile.

## First use

Open Settings in the client, choose `Create account`, then use the same account on another device. The server has no default password. Each Pi can register as a device through the authenticated `/devices` endpoint; keep the returned device key private. The current UI can use the shared account token and is designed to add per-device enrollment next.

## What works away from home

At home, away on another Wi-Fi network, through a phone hotspot, and on public Wi-Fi, the Pi only needs outbound Internet access and Tailscale connectivity. Public Wi-Fi that requires a browser captive portal must be accepted once in a browser before the app can connect. If home Internet or the VM is down, server messaging, presence, account sync, and calls stop; the clock, UI, dialer screen, Wi-Fi settings, and local features continue.

## Calls and messaging

The message API provides history and WebSocket delivery. Messages composed while Wi-Fi is unavailable are queued in the client configuration directory and retried after reconnection; messages already accepted by the server remain in SQLite and are returned on the next history request. The current call button is deliberately signaling-only. For audio between your own devices, add a WebRTC SFU such as Janus or Jitsi behind Tailscale, or use SIP with Asterisk/FreeSWITCH and a SIP client. For real phone numbers, purchase/configure a SIP trunk from a provider and route calls through Asterisk or FreeSWITCH. That provider is the part that supplies PSTN access and a phone number; the Pi still uses Wi-Fi.

## JARVIS API contract

Use the authenticated server as the stable bridge. A future JARVIS service can accept `POST /jarvis/prompt` with `{ "text": "...", "device_id": "..." }`, `POST /jarvis/audio` for an uploaded audio clip, and return `{ "text": "...", "tts_url": "...", "commands": [] }`. Keep JARVIS local on the VM or Pi; no cloud AI is required for the phone's basic functions.

## Troubleshooting

- `Server unreachable`: confirm Wi-Fi, `tailscale status`, and `curl https://YOUR_TAILSCALE_URL/health`.
- `401`: sign out and sign in again; tokens expire after 12 hours.
- `502` from Serve: check `sudo systemctl status rpi-phone` and `journalctl -u rpi-phone`.
- No Wi-Fi list: ensure `NetworkManager` is active and the Pi's Wi-Fi interface is unblocked with `rfkill list`.
- Blank Qt window: run `QT_QPA_PLATFORM=linuxfb` only for framebuffer deployments; on Raspberry Pi OS desktop use the default X11/Wayland platform.
- Hotspot disconnects: disable phone battery optimization for hotspot and verify the hotspot allows VPN traffic.

## Updates and backups

```bash
# server update
sudo systemctl stop rpi-phone
cp -a /opt/rpi-phone/server/database/phone.db /opt/rpi-phone/backups/phone-$(date +%F).db
# copy the new server files, then:
cd /opt/rpi-phone/server && .venv/bin/pip install -r requirements.txt
sudo systemctl start rpi-phone

# database backup only
sqlite3 /opt/rpi-phone/server/database/phone.db ".backup '/opt/rpi-phone/backups/phone-$(date +%F-%H%M).db'"
```

Back up `server/database/phone.db` and `server/config/server.env` securely. Never commit either file. To add another Pi, install the client, install Tailscale, copy a client config with the same server URL, and create a separate user or authenticated device registration; do not share session files between devices.
