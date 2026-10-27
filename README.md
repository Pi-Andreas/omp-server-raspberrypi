# open.mp server for Raspberry Pi

The [open.mp](https://github.com/openmultiplayer/open.mp) server, built for
**Raspberry Pi 4 / 5 running 64-bit Raspberry Pi OS** (or any arm64 Linux).

This repo is a fork of upstream open.mp. Everything on top of upstream is in
a few commits, listed at
[the compare view](https://github.com/openmultiplayer/open.mp/compare/master...Pi-Andreas:omp-server-raspberrypi:master):
an arm64 build in Docker, a deploy script, a systemd unit and one upstream
crash fix. Nothing is compiled on the Pi itself.

### Requirements

- **Raspberry Pi 4 or 5** with a **64-bit** OS (`uname -m` prints `aarch64`).
  32-bit Raspberry Pi OS is not supported.
- Raspberry Pi OS bookworm (Debian 12) or newer; the build needs glibc 2.36.

### Install from a release

On the Pi:

```bash
curl -LO https://github.com/Pi-Andreas/omp-server-raspberrypi/releases/latest/download/open.mp-linux-arm64.tar.gz
tar -xzf open.mp-linux-arm64.tar.gz
cd omp-server
./omp-server --default-config
```

That unpacks to `~/omp-server` (the server, `components/`, empty
`gamemodes/`, `filterscripts/` etc. and `omp-server.service`) and writes a
default `config.json`. Then:

1. Copy your gamemode (`.amx`) into `gamemodes/` and name it in
   `config.json` under `pawn.main_scripts`, for example `"mygamemode 1"`.
2. Change `rcon.password` from `changeme` (or set `rcon.enable` to `false`).
   The server exits at startup while the default password is set.
3. Start it with `./omp-server`.

Compiled `.amx` scripts are platform independent, so gamemodes built on
Windows, macOS or Linux run unchanged. Players connect on UDP port **7777**;
forward it on your router to make the server public.

### Run at boot

`omp-server.service` keeps the server running and starts it at boot. Edit the
user and paths in it (it assumes user `pi` and `/home/pi/omp-server`), then:

```bash
sudo cp omp-server.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now omp-server
journalctl -u omp-server -f
```

### Build it yourself

Any machine with Docker can build it. An Apple Silicon Mac or other arm64
host builds natively; an x86 host emulates arm64 and is much slower.

```bash
git clone --recursive https://github.com/Pi-Andreas/omp-server-raspberrypi
cd omp-server-raspberrypi
./raspberrypi/build.sh
PI=pi@raspberrypi.local ./raspberrypi/deploy.sh
```

| Path | What it does |
|---|---|
| `raspberrypi/build.sh` | Builds the server for linux/arm64 in a Debian 12 container and packs it into `raspberrypi/dist/open.mp-linux-arm64.tar.gz`. |
| `raspberrypi/deploy.sh` | Copies that tarball to the Pi over SSH and unpacks it into `~/omp-server`, keeping your config and scripts. |
| `raspberrypi/omp-server.service` | systemd unit (also shipped in the tarball). |

OpenSSL and libstdc++ are linked statically. The first build downloads and
compiles the Conan dependencies, which takes a while; they are cached in
`raspberrypi/.conan2` for later builds.

### Notes

- **Plugins:** only Linux **arm64** `.so` plugins load. Most legacy SA-MP
  plugins ship only as 32-bit x86 builds and will not work on the Pi.
- **Memory:** an idle server running a small gamemode uses about 100 MB of
  RAM, so a 1 GB Pi 4 is enough for small servers.

---

# open.mp

![status](https://github.com/openmultiplayer/open.mp/workflows/Build/badge.svg)

## Structure

| Path | Content |
| ---- | ------- |
| `SDK/include` | Core SDK headers (stable between versions) |
| `SDK/include/Server/Components/*/` | Components/plug-in SDK headers (stable between versions) |
| `Shared/NetCode/` | Netcode headers (RPC and packet read/write structures, NOT stable between versions) |
| `Shared/Network/` | Network utility headers (NOT stable between versions) |
| `lib/` | Various submodules and third-party libraries |
| `Server/Source/` | Core server implementation (NOT stable between versions, do NOT use headers outside the Source folder) |
| `Server/Components/*/` | Components/plug-in implementation (NOT stable between versions, do NOT use headers outside the component's folder) |

## Concepts

| Name | Description |
| ---- | ------- |
| Entity | Something that can appear in the 3D world of the game |
| Pool | Container of something with limited amount of IDs |
| Component | Something that's conceptually different enough it can be separated into its own module |
| Extensible | Something to which extensions can be added to preserve ABI compatibility |
| Extension | Something which adds additional functionality to an extensible and preserves ABI compatibility |

## Building

See [BUILD.md](BUILD.md) for source checkout, prerequisites, and build instructions for Windows, Linux, and macOS.
