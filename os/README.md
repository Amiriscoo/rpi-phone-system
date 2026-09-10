# Pi Phone OS image

This directory builds a custom Raspberry Pi Linux image using `pi-gen`. It is a Pi Phone distribution based on Raspberry Pi OS Bookworm, not a new kernel or a copy of iOS/Android. It retains Linux hardware support for HDMI monitors, USB keyboards, USB mice, Bluetooth, Wi-Fi, NetworkManager, SSH, and Raspberry Pi peripherals.

## Build the image

Build on Ubuntu/Debian, WSL2, or a Linux VM. Do not run this directly in Windows PowerShell.

```bash
sudo apt update
sudo apt install -y git coreutils quilt parted qemu-user-static debootstrap zerofree zip dosfstools libarchive-tools libcap2-bin rsync xz-utils kmod bc
cd rpi_phone_system
bash os/build.sh
```

The first build downloads `pi-gen` and can take a while. The image is written to `os/images`. Flash the generated `.img` file with Raspberry Pi Imager or Raspberry Pi Etcher.

The builder prompts for the initial `pi` account password and does not store it in this repository. Change it later with:

```bash
passwd
```

Then set the server URL in `/opt/rpi-phone/client/config/client.json`, install Tailscale, and authenticate the device:

```bash
sudo tailscale up
sudo systemctl restart rpi-phone-client
```

## Hardware modes

- Pi 4/5: HDMI, USB mouse, USB keyboard, touchscreen, Wi-Fi, and Bluetooth are supported.
- Pi Zero 2 W: touchscreen and HDMI work; Bluetooth input works. Its single OTG port cannot be both a USB gadget and a USB host simultaneously.
- The image starts the Pi Phone client in windowed mode. Run `sudo systemctl edit rpi-phone-client` and add `--fullscreen` to `ExecStart` for a touchscreen kiosk.

The image recipe does not embed Wi-Fi passwords, Tailscale keys, server secrets, or user sessions.