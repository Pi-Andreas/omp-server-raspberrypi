# open.mp server for Raspberry Pi

The [open.mp](https://github.com/openmultiplayer/open.mp) server, built for
**Raspberry Pi 4 / 5 running 64-bit Raspberry Pi OS** (or any arm64 Linux).
The code is upstream open.mp; this repo adds a build that targets arm64 and a
way to get it onto the Pi. Nothing is compiled on the Pi itself.

| Path | What it does |
|---|---|
| `raspberrypi/build.sh` | Builds the server for linux/arm64 in Docker and packs it into `raspberrypi/dist/open.mp-linux-arm64.tar.gz`. |
| `raspberrypi/deploy.sh` | Copies that tarball to the Pi over SSH and unpacks it into `~/omp-server`. |
| `raspberrypi/omp-server.service` | systemd unit to keep the server running and start it at boot. |

### Requirements

- **Raspberry Pi 4 or 5** with a **64-bit** OS (`uname -m` prints `aarch64`).
  32-bit Raspberry Pi OS is not supported.
- To build: any machine with Docker. An Apple Silicon Mac or other arm64 host
  builds natively; an x86 host emulates arm64 and is much slower.

### Build

```bash
git clone --recursive https://github.com/Mac-Andreas/omp-server-raspberrypi
cd omp-server-raspberrypi
./raspberrypi/build.sh
```

The build image is Debian 12 (glibc 2.36), so the binary runs on Raspberry
Pi OS bookworm and newer. OpenSSL and libstdc++ are linked statically. The
first build downloads and compiles the Conan dependencies, which takes a
while; they are cached in `raspberrypi/.conan2` for later builds.

### Install on the Pi

```bash
PI=pi@raspberrypi.local ./raspberrypi/deploy.sh
```

Then on the Pi, write a default `config.json`, add your gamemode (`.amx`) to
`~/omp-server/gamemodes`, name it in `config.json` under `pawn.main_scripts`
(for example `"mygamemode 1"`), and start the server:

```bash
cd ~/omp-server
./omp-server --default-config
nano config.json
./omp-server
```

Also change `rcon.password` from `changeme` (or set `rcon.enable` to
`false`); the server exits at startup while the default password is set.

Compiled `.amx` scripts are platform independent, so gamemodes built on
Windows, macOS or Linux run unchanged. Players connect on UDP port **7777**;
forward it on your router to make the server public.

To keep it running in the background and start it at boot, see
[`raspberrypi/omp-server.service`](raspberrypi/omp-server.service).

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
