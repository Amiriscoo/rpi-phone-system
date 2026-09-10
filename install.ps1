$ErrorActionPreference = "Stop"

$root = (Resolve-Path (Join-Path $PSScriptRoot ".")).Path
$wslPath = (& wsl.exe wslpath -a -u $root).Trim()
if (-not $wslPath) {
    throw "WSL2 is required. Install Ubuntu from the Microsoft Store, then run this installer again."
}

Write-Host "Starting the Pi Phone OS builder inside WSL2..."
& wsl.exe bash -lc "cd '$wslPath' && bash install.sh"
if ($LASTEXITCODE -ne 0) {
    throw "The image build failed with exit code $LASTEXITCODE."
}

Write-Host "The flashable image is in os/images."