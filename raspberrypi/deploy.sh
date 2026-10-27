#!/usr/bin/env bash
# Copy the server built by build.sh to a Raspberry Pi and unpack it there.
#
#   PI=pi@raspberrypi.local ./raspberrypi/deploy.sh
#
# Installs into ~/omp-server on the Pi (override with DEST=...). An existing
# config.json, gamemodes/, filterscripts/, scriptfiles/ and plugins/ are kept;
# only the server binary and components/ are replaced.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TARBALL="$ROOT/raspberrypi/dist/open.mp-linux-arm64.tar.gz"
PI="${PI:?set PI=user@host of the Raspberry Pi}"
DEST="${DEST:-omp-server}"

[ -f "$TARBALL" ] || { echo "no $TARBALL - run raspberrypi/build.sh first" >&2; exit 1; }

scp "$TARBALL" "$PI:/tmp/open.mp-linux-arm64.tar.gz"
ssh "$PI" DEST="$DEST" bash -s <<'REMOTE'
set -euo pipefail
cd ~
mkdir -p "$DEST"
rm -rf "$DEST/components"
tar -C "$DEST" --strip-components=1 -xzf /tmp/open.mp-linux-arm64.tar.gz
rm -f /tmp/open.mp-linux-arm64.tar.gz
echo "installed to ~/$DEST:"
ls "$DEST"
REMOTE
