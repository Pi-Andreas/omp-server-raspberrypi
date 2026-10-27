#!/usr/bin/env python3
"""Track how much of a Raspberry Pi an open.mp server uses.

    ./omp-usage.py record [--interval 60]   append a sample every interval
    ./omp-usage.py report [--days 7]        summarise the samples

Run it from the server folder (or pass --dir). Each sample records the
players online (asked from the server's own query port), the server's CPU
(percent of one core; the main thread is what limits player count) and
memory, the traffic on the Pi's main network interface, free memory, the
CPU temperature and throttling flags. Samples go to
usage/usage-YYYY-MM.csv in the server folder.

The report fits CPU and upload against player count, so once real players
have been on, it shows the cost per player on this Pi and how many players
it can take.
"""

import argparse
import csv
import glob
import json
import os
import shutil
import socket
import struct
import subprocess
import sys
import time
from datetime import datetime, timedelta

FIELDS = [
    "time", "players", "max_players", "cpu_pct", "main_thread_pct",
    "system_cpu_pct", "rss_mb", "mem_available_mb", "rx_kbps", "tx_kbps",
    "temp_c", "throttled",
]
CLK_TCK = os.sysconf("SC_CLK_TCK")


def find_server(server_dir):
    """PID of the omp-server running from server_dir, else any omp-server."""
    fallback = None
    for path in glob.glob("/proc/[0-9]*/cmdline"):
        pid = int(path.split("/")[2])
        try:
            with open(path, "rb") as f:
                exe = f.read().split(b"\0")[0]
            if os.path.basename(exe) != b"omp-server":
                continue
            if os.path.realpath(f"/proc/{pid}/cwd") == os.path.realpath(server_dir):
                return pid
            fallback = fallback or pid
        except OSError:
            continue
    return fallback


def proc_ticks(pid, tid=None):
    """utime + stime of a process (or one of its threads), in clock ticks."""
    path = f"/proc/{pid}/task/{tid}/stat" if tid else f"/proc/{pid}/stat"
    with open(path) as f:
        fields = f.read().rsplit(")", 1)[1].split()
    return int(fields[11]) + int(fields[12])


def rss_mb(pid):
    with open(f"/proc/{pid}/status") as f:
        for line in f:
            if line.startswith("VmRSS:"):
                return int(line.split()[1]) / 1024
    return 0.0


def system_ticks():
    with open("/proc/stat") as f:
        values = [int(v) for v in f.readline().split()[1:]]
    idle = values[3] + values[4]
    return sum(values), idle


def mem_available_mb():
    with open("/proc/meminfo") as f:
        for line in f:
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) / 1024
    return 0.0


def default_interface():
    with open("/proc/net/route") as f:
        for line in f.readlines()[1:]:
            parts = line.split()
            if parts[1] == "00000000":
                return parts[0]
    return None


def net_bytes(iface):
    with open("/proc/net/dev") as f:
        for line in f:
            name, _, data = line.partition(":")
            if name.strip() == iface:
                values = data.split()
                return int(values[0]), int(values[8])
    return 0, 0


def temperature():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            return int(f.read()) / 1000
    except OSError:
        return None


def throttled():
    """vcgencmd's throttle flags, e.g. 0x0 (none) or 0x50005 (under-voltage)."""
    if not shutil.which("vcgencmd"):
        return ""
    try:
        out = subprocess.run(["vcgencmd", "get_throttled"], capture_output=True,
                             text=True, timeout=5).stdout
        return out.strip().partition("=")[2]
    except (OSError, subprocess.SubprocessError):
        return ""


def server_port(server_dir):
    try:
        with open(os.path.join(server_dir, "config.json")) as f:
            return int(json.load(f).get("network", {}).get("port", 7777))
    except (OSError, ValueError):
        return 7777


def query_players(port):
    """(players, max_players) from the SA-MP query protocol, or (None, None)."""
    header = b"SAMP" + bytes([127, 0, 0, 1]) + struct.pack("<H", port)
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(2)
            s.sendto(header + b"i", ("127.0.0.1", port))
            data = s.recv(2048)[11:]
        return struct.unpack("<H", data[1:3])[0], struct.unpack("<H", data[3:5])[0]
    except (OSError, struct.error):
        return None, None


def log_path(server_dir, when):
    folder = os.path.join(server_dir, "usage")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, f"usage-{when:%Y-%m}.csv")


def record(args):
    server_dir = args.dir
    iface = default_interface()
    port = server_port(server_dir)
    print(f"recording every {args.interval}s from {server_dir} "
          f"(query port {port}, interface {iface})", flush=True)

    pid = prev = None
    while True:
        now_pid = find_server(server_dir)
        if now_pid != pid:
            pid, prev = now_pid, None
        counters = None
        if pid:
            try:
                counters = (time.monotonic(), proc_ticks(pid), proc_ticks(pid, pid),
                            *system_ticks(), *net_bytes(iface))
            except OSError:
                pid = None
        if prev and counters:
            elapsed = counters[0] - prev[0]
            total, idle = counters[3] - prev[3], counters[4] - prev[4]
            players, max_players = query_players(port)
            temp = temperature()
            row = {
                "time": datetime.now().isoformat(timespec="seconds"),
                "players": "" if players is None else players,
                "max_players": "" if max_players is None else max_players,
                "cpu_pct": round(100 * (counters[1] - prev[1]) / CLK_TCK / elapsed, 1),
                "main_thread_pct": round(100 * (counters[2] - prev[2]) / CLK_TCK / elapsed, 1),
                "system_cpu_pct": round(100 * (total - idle) / total, 1) if total else 0,
                "rss_mb": round(rss_mb(pid), 1),
                "mem_available_mb": round(mem_available_mb()),
                "rx_kbps": round((counters[5] - prev[5]) * 8 / 1000 / elapsed, 1),
                "tx_kbps": round((counters[6] - prev[6]) * 8 / 1000 / elapsed, 1),
                "temp_c": "" if temp is None else round(temp, 1),
                "throttled": throttled(),
            }
            path = log_path(server_dir, datetime.now())
            new_file = not os.path.exists(path)
            with open(path, "a", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=FIELDS)
                if new_file:
                    writer.writeheader()
                writer.writerow(row)
        prev = counters
        time.sleep(args.interval)


def fit(xs, ys):
    """Least-squares y = a + b*x; None without enough spread in x."""
    n = len(xs)
    if n < 10 or len(set(xs)) < 3:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0:
        return None
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    return my - b * mx, b


def pct(values, p):
    values = sorted(values)
    return values[min(len(values) - 1, int(p / 100 * len(values)))]


def report(args):
    since = datetime.now() - timedelta(days=args.days)
    rows = []
    for path in sorted(glob.glob(os.path.join(args.dir, "usage", "usage-*.csv"))):
        with open(path, newline="") as f:
            for row in csv.DictReader(f):
                if datetime.fromisoformat(row["time"]) >= since and row["players"] != "":
                    rows.append(row)
    if not rows:
        sys.exit("no samples yet - run `omp-usage.py record` first")

    def col(name):
        return [float(r[name]) for r in rows if r[name] != ""]

    players = col("players")
    print(f"{len(rows)} samples, {rows[0]['time']} to {rows[-1]['time']}")
    print(f"players          avg {sum(players) / len(players):6.1f}   peak {max(players):6.0f}"
          f"   (max_players {rows[-1]['max_players']})")
    for name, label, unit in [
        ("main_thread_pct", "main thread", "% of a core"),
        ("cpu_pct", "server CPU", "% of a core"),
        ("system_cpu_pct", "whole Pi CPU", "%"),
        ("rss_mb", "server RAM", "MB"),
        ("mem_available_mb", "free RAM", "MB"),
        ("tx_kbps", "upload", "kbit/s"),
        ("rx_kbps", "download", "kbit/s"),
        ("temp_c", "temperature", "C"),
    ]:
        values = col(name)
        if values:
            print(f"{label:16} avg {sum(values) / len(values):6.1f}   p95 {pct(values, 95):6.1f}"
                  f"   peak {max(values):6.1f}  {unit}")
    flags = {r["throttled"] for r in rows if r["throttled"] not in ("", "0x0")}
    if flags:
        print(f"throttling seen: {', '.join(sorted(flags))} (check power supply and cooling)")

    cpu = fit(players, [float(r["main_thread_pct"]) for r in rows])
    up = fit(players, [float(r["tx_kbps"]) for r in rows])
    if not cpu or not up:
        print("\nper-player cost: needs samples at several different player counts")
        return
    print(f"\nper player: {cpu[1]:.2f}% of a core, {up[1]:.1f} kbit/s upload")
    if cpu[1] > 0:
        print(f"main thread reaches 80% of a core at about {(80 - cpu[0]) / cpu[1]:.0f} players")
    for n in (50, 100, 200, 300, 500):
        print(f"  {n:4} players: ~{cpu[0] + cpu[1] * n:5.1f}% of a core, "
              f"~{(up[0] + up[1] * n) / 1000:5.1f} Mbit/s upload")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--dir", default=os.getcwd(), help="server folder (default: current)")
    sub = parser.add_subparsers(dest="command", required=True)
    rec = sub.add_parser("record", help="append a sample every --interval seconds")
    rec.add_argument("--interval", type=int, default=60)
    rep = sub.add_parser("report", help="summarise recorded samples")
    rep.add_argument("--days", type=float, default=7)
    args = parser.parse_args()
    (record if args.command == "record" else report)(args)


if __name__ == "__main__":
    main()
