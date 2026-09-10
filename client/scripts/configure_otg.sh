#!/usr/bin/env bash
set -euo pipefail

if [[ "$(id -u)" -ne 0 ]]; then
    echo "Run with sudo: sudo bash ./scripts/configure_otg.sh"
    exit 1
fi

BOOT_DIR="/boot/firmware"
CONFIG_FILE="$BOOT_DIR/config.txt"
CMDLINE_FILE="$BOOT_DIR/cmdline.txt"

if [[ ! -f "$CONFIG_FILE" || ! -f "$CMDLINE_FILE" ]]; then
    echo "This script expects Raspberry Pi OS Bookworm files under $BOOT_DIR."
    exit 1
fi

if ! grep -qxF 'dtoverlay=dwc2' "$CONFIG_FILE"; then
    printf '\ndtoverlay=dwc2\n' >> "$CONFIG_FILE"
fi

if ! grep -q 'modules-load=dwc2,g_ether' "$CMDLINE_FILE"; then
    sed -i 's/$/ modules-load=dwc2,g_ether/' "$CMDLINE_FILE"
fi

echo "USB Ethernet gadget mode is configured. Reboot the Pi."
echo "Connect the host computer to the Pi Zero 2 W OTG data port."
echo "Disable gadget mode by removing dtoverlay=dwc2 and modules-load=dwc2,g_ether from the boot files."