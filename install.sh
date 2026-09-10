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
if apt-cache show qemu-user-binfmt >/dev/null 2>&1; then
    QEMU_PACKAGE="qemu-user-binfmt"
else
    QEMU_PACKAGE="qemu-user-static"
fi
echo "Using QEMU provider: $QEMU_PACKAGE"

if [[ "$QEMU_PACKAGE" != "qemu-user-static" ]]; then
    sudo dpkg --purge --force-all qemu-user-static >/dev/null 2>&1 || true
fi

sudo apt-get install -y git coreutils quilt parted "$QEMU_PACKAGE" debootstrap zerofree zip dosfstools libarchive-tools libcap2-bin rsync xz-utils kmod bc pigz arch-test

if [[ "$QEMU_PACKAGE" == "qemu-user-binfmt" ]]; then
    QEMU_ARM="$(command -v qemu-arm || true)"
    if [[ -z "$QEMU_ARM" ]]; then
        echo "qemu-user-binfmt installed but qemu-arm was not found."
        exit 1
    fi
    sudo ln -sfn "$QEMU_ARM" /usr/local/bin/qemu-arm-static
fi


cd "$ROOT_DIR"
exec bash os/build.sh