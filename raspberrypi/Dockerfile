# Build environment for the open.mp server on Raspberry Pi (64-bit ARM).
# Debian 12 (bookworm) keeps glibc at 2.36, so the binaries also run on newer
# Raspberry Pi OS / Debian releases (trixie and later).
FROM --platform=linux/arm64 debian:bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential clang lld cmake ninja-build git perl pkg-config \
        python3 python3-venv ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Upstream only supports building with Clang; make it the default compiler
# (also for the Conan profile detected below).
ENV CC=clang CXX=clang++

# Conan 2 (upstream's cmake-conan rejects 1.x), isolated from Debian's Python.
RUN python3 -m venv /opt/conan \
    && /opt/conan/bin/pip install --no-cache-dir conan \
    && /opt/conan/bin/conan profile detect
ENV PATH=/opt/conan/bin:$PATH
