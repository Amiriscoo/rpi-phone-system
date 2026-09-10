#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ "$(uname -s)" != "Linux" ]]; then
    echo "Use install.ps1 from Windows, or run this script inside WSL2/Linux."
    exit 1
fi

if ! command -v sudo >/dev/null 2>&1; then
    echo "sudo is required to install the image-builder dependencies."
    exit 1
fi

sudo apt-get update
if apt-cache show qemu-user-static >/dev/null 2>&1; then
    QEMU_PACKAGE="qemu-user-static"
else
    QEMU_PACKAGE="qemu-user-binfmt"
fi
sudo apt-get install -y git coreutils quilt parted "$QEMU_PACKAGE" debootstrap zerofree zip dosfstools libarchive-tools libcap2-bin rsync xz-utils kmod bc

cd "$ROOT_DIR"
exec bash os/build.sh