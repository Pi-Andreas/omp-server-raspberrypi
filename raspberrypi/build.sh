#!/usr/bin/env bash
# Build the open.mp server for Raspberry Pi (linux arm64) inside Docker and
# package it as raspberrypi/dist/open.mp-linux-arm64.tar.gz.
#
# Runs on any Docker host; on Apple Silicon or another arm64 machine the
# container runs natively, elsewhere Docker emulates arm64 (slow).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
IMAGE=omp-server-raspberrypi-build
BUILD_DIR=build-raspberrypi
CONFIG="${CONFIG:-RelWithDebInfo}"

docker build --platform linux/arm64 -t "$IMAGE" "$ROOT/raspberrypi"

# The Conan cache is kept on the host so rebuilds don't recompile OpenSSL etc.
mkdir -p "$ROOT/raspberrypi/.conan2"
# Same build number and commit stamping as upstream's docker/build.sh.
docker run --rm --platform linux/arm64 \
    -e OMP_BUILD_VERSION="$(git -C "$ROOT" rev-list $(git -C "$ROOT" rev-list --max-parents=0 HEAD) HEAD | wc -l | tr -d ' ')" \
    -e OMP_BUILD_COMMIT="$(git -C "$ROOT" rev-parse HEAD)" \
    -v "$ROOT:/src" \
    -v "$ROOT/raspberrypi/.conan2:/root/.conan2" \
    -w /src \
    "$IMAGE" bash -c "
        set -e
        conan profile detect --exist-ok >/dev/null
        cmake -S . -B $BUILD_DIR -G Ninja \
            -DCMAKE_BUILD_TYPE=$CONFIG \
            -DTARGET_BUILD_ARCH=armv8 \
            -DSHARED_OPENSSL=false \
            -DSTATIC_STDCXX=true \
            -DBUILD_SERVER=1 \
            -DBUILD_ABI_CHECK_TOOL=0 \
            -DCMAKE_POLICY_VERSION_MINIMUM=3.5
        cmake --build $BUILD_DIR --config $CONFIG --parallel \"\$(nproc)\"
    "

OUT="$ROOT/$BUILD_DIR/Output/$CONFIG/Server"
DIST="$ROOT/raspberrypi/dist"
# The archive unpacks to omp-server/, ready to run, with the usual empty
# script folders, the systemd units and the usage tracker next to the binary.
STAGE="$DIST/omp-server"
rm -rf "$STAGE"
mkdir -p "$STAGE"/{gamemodes,filterscripts,scriptfiles,plugins,models}
cp -R "$OUT/omp-server" "$OUT/components" "$STAGE/"
cp "$ROOT/raspberrypi/omp-server.service" "$ROOT/raspberrypi/omp-usage.service" \
    "$ROOT/raspberrypi/omp-usage.py" "$STAGE/"
# No macOS ._* AppleDouble files or extended attributes in the archive.
COPYFILE_DISABLE=1 tar --no-xattrs -C "$DIST" -czf "$DIST/open.mp-linux-arm64.tar.gz" omp-server
echo "built: $DIST/open.mp-linux-arm64.tar.gz"
