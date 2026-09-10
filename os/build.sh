#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PI_GEN_DIR="${PI_GEN_DIR:-$ROOT_DIR/.pi-gen}"
OUTPUT_DIR="${OUTPUT_DIR:-$ROOT_DIR/os/images}"

if [[ "$(uname -s)" != "Linux" ]]; then
    echo "Build this image inside Ubuntu/Debian, WSL2, or a Linux VM."
    exit 1
fi

if [[ "$(id -u)" -eq 0 ]]; then
    echo "Run as a normal user. pi-gen invokes sudo when required."
    exit 1
fi

read -r -s -p "Password for the first-boot pi user: " PI_PASSWORD
echo
read -r -s -p "Repeat the pi user password: " PI_PASSWORD_CONFIRM
echo
if [[ -z "$PI_PASSWORD" || "$PI_PASSWORD" != "$PI_PASSWORD_CONFIRM" ]]; then
    echo "Passwords are empty or do not match."
    exit 1
fi
printf -v PI_PASSWORD_CONFIG '%q' "$PI_PASSWORD"

if [[ ! -d "$PI_GEN_DIR" ]]; then
    git clone --depth=1 --branch bookworm https://github.com/RPi-Distro/pi-gen.git "$PI_GEN_DIR"
else
    git -C "$PI_GEN_DIR" fetch --depth=1 origin bookworm
    git -C "$PI_GEN_DIR" checkout -q -B bookworm FETCH_HEAD
fi

sudo rm -rf "$PI_GEN_DIR/stage-rpi-phone"
sudo rm -rf "$PI_GEN_DIR/work" "$PI_GEN_DIR/deploy"
cp -a "$ROOT_DIR/os/stage-rpi-phone" "$PI_GEN_DIR/stage-rpi-phone"
mkdir -p "$PI_GEN_DIR/stage-rpi-phone/files/opt/rpi-phone/client"
cp -a "$ROOT_DIR/client/." "$PI_GEN_DIR/stage-rpi-phone/files/opt/rpi-phone/client/"
mkdir -p "$OUTPUT_DIR"

if dpkg-query -W -f='${Status}' qemu-user-binfmt 2>/dev/null | grep -q 'install ok installed'; then
    sed -i 's/^qemu-user-static$/qemu-user-binfmt/' "$PI_GEN_DIR/depends"
fi

cat > "$PI_GEN_DIR/config" <<CONFIG
IMG_NAME='pi-phone'
RELEASE='bookworm'
FIRST_USER_NAME='pi'
FIRST_USER_PASS=$PI_PASSWORD_CONFIG
DISABLE_FIRST_BOOT_USER_RENAME=1
ENABLE_SSH=1
STAGE_LIST='stage0 stage1 stage2 stage3 stage4 stage5 stage-rpi-phone'
DEPLOY_DIR="$OUTPUT_DIR"
CONFIG

echo "Building Pi Phone OS image. The password is supplied only to this local build."
cd "$PI_GEN_DIR"
sudo ./build.sh