# open.mp server for Raspberry Pi

The [open.mp](https://github.com/openmultiplayer/open.mp) server, built for
**Raspberry Pi 4 / 5 running 64-bit Raspberry Pi OS** (or any arm64 Linux).

This repo is a fork of upstream open.mp. Everything on top of upstream is in
a few commits, listed at
[the compare view](https://github.com/openmultiplayer/open.mp/compare/master...Pi-Andreas:omp-server-raspberrypi:master):
an arm64 build in Docker, a deploy script, systemd units, a usage tracker
and one upstream crash fix. Nothing is compiled on the Pi itself.

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
`gamemodes/`, `filterscripts/` etc., `omp-server.service` and the usage
tracker `omp-usage.py`) and writes a
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

### Track usage

`omp-usage.py` (in the same folder) records a sample every minute: players
online, the server's CPU and memory, upload and download on the Pi's network
interface, free memory, temperature and throttling flags. Samples go to
`usage/usage-YYYY-MM.csv`.

```bash
./omp-usage.py record &      # or install omp-usage.service to run it at boot
./omp-usage.py report        # summary of the last 7 days (--days N)
```

Once real players have been on at different player counts, the report also
fits CPU and upload against players and prints the cost per player on that Pi
and the player count at which the main thread would reach 80% of a core.
Throttling flags other than `0x0` mean the Pi is short on power or cooling.

### Capacity and which Pi to use

**Measured** on a Raspberry Pi 4 Model B (1.8 GHz, 1 GB) with server-side
NPCs jogging around a 1 km square of Los Santos (default 200 m stream radius),
averaged over 30 s:

| Moving NPCs | Main thread (% of one core) | Server RAM |
|---:|---:|---:|
| 0 | 0.5% | 96 MB |
| 100 | 3.8% | 145 MB |
| 200 | 7.9% | 153 MB |
| 400 | 11.0% | 169 MB |
| 700 | 24.5% | 194 MB |
| 990 | 41.8% | 219 MB |

The game loop runs on one core, so "% of one core" is what limits player
count. The Pi stayed at 40 °C with no throttling. NPCs cover simulation and
streaming but not networking or gamemode scripts, so a real player costs more:
the estimates below assume 3–5 times the NPC cost per player.

**Bandwidth** (estimated from the sync protocol; the tracker measures the
real figure): a moving player sends about 30 sync packets a second, roughly
25–30 kbit/s of download per player. The server relays each player's sync to
every player streamed near them, about 12 kbit/s per nearby moving player.

| Server style | Upload per player | 50 players | 100 players | 200 players |
|---|---:|---:|---:|---:|
| Spread out (RP, freeroam; ~8 nearby) | ~60 kbit/s | ~3 Mbit/s | ~6 Mbit/s | ~12 Mbit/s |
| Crowded (DM, events; ~20 nearby) | ~150–250 kbit/s | ~8–12 Mbit/s | ~15–25 Mbit/s | ~30–50 Mbit/s |

On a home connection the upload speed is usually the real limit, not the Pi.

**Which Pi** (player counts assume a typical gamemode and enough upload):

| Model | One core vs Pi 4 | Comfortable players | Notes |
|---|---:|---:|---|
| Pi 5 (4 or 8 GB) | ~2–3× | 300+ | Big or script-heavy servers, or MySQL on the same Pi. Needs the 27 W supply and active cooling. |
| **Pi 4 (2 GB)** | 1× (measured) | ~150–200 | Best value. 1 GB is enough for the server alone; 4 GB if MySQL runs on the same Pi. |
| Pi 3B / 3B+ | ~0.4× | up to ~50 | Small servers. Ethernet is limited to ~300 Mbit/s (USB 2). |
| Zero 2 W | ~0.3× | private only | 512 MB and Wi-Fi only; not recommended. |

Use wired Ethernet rather than Wi-Fi, the official power supply (under-voltage
throttles the CPU) and a heatsink or fan for long sessions. The server needs
about 100 MB plus ~0.1 MB per player slot; MySQL 8 on the same Pi adds about
400 MB (MariaDB less).

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
| `raspberrypi/omp-usage.py`, `omp-usage.service` | Usage tracker and its systemd unit (also shipped in the tarball). |

OpenSSL and libstdc++ are linked statically. The first build downloads and
compiles the Conan dependencies, which takes a while; they are cached in
`raspberrypi/.conan2` for later builds.

### Plugins and components on the Pi

Only Linux **arm64** `.so` builds load on the Pi; most legacy SA-MP plugins
ship only as 32-bit x86 builds. These have Pi builds, each released as a
tarball you unpack in the server folder:

| Plugin | Pi build | Notes |
|---|---|---|
| ColAndreas 1.4.0 | [Pi-Andreas/ColAndreas-raspberrypi](https://github.com/Pi-Andreas/ColAndreas-raspberrypi/releases/latest) | Bundles its Bullet libraries. Bring your own `ColAndreas.cadb`. The collision world uses a few hundred MB of RAM. |
| MapAndreas 1.2.1 | [Pi-Andreas/samp-plugin-mapandreas-raspberrypi](https://github.com/Pi-Andreas/samp-plugin-mapandreas-raspberrypi/releases/latest) | Includes both heightmaps and a fix for a crash on server shutdown. |
| omp-MySQL | [Mac-Andreas/omp-MySQL](https://github.com/Mac-Andreas/omp-MySQL/releases) | open.mp component; `mysql-linux-arm64.zip` from v1.0.2. Tested against MySQL 8.4 over TLS 1.3. |
| streamer 2.9.6 | [Pi-Andreas/samp-streamer-plugin-raspberrypi](https://github.com/Pi-Andreas/samp-streamer-plugin-raspberrypi) | **In progress.** Its sampgdk library hooks the server by patching x86 machine code, which has to be ported to ARM first. |

### Notes

- **Memory:** an idle server running a small gamemode uses about 100 MB of
  RAM, so a 1 GB Pi 4 is enough for small servers. With ColAndreas and
  MapAndreas (full heightmap) loaded the server uses about 500 MB, so take a
  2 GB Pi or larger for a full gamemode.

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
