"""System & Process Resource Monitor.

Captures CPU, RAM (RSS/VMS), open file descriptors/handles, and network I/O
every 1 second, writing to a timestamped CSV trace for soak & breaking-point analysis.
"""
from __future__ import annotations

import csv
import os
import sys
import time
from pathlib import Path
import psutil

# Windows handle count
def get_handles_or_fds(proc: psutil.Process) -> int:
    try:
        if sys.platform == "win32":
            return proc.num_handles()
        return proc.num_fds()
    except Exception:
        return 0


class SystemMonitor:
    def __init__(self, output_csv: Path, target_pid: int | None = None):
        self.output_csv = output_csv
        self.target_pid = target_pid
        self.running = False
        self._target_proc = psutil.Process(target_pid) if target_pid else None

    def start_sampling(self, duration_seconds: float = 60.0, interval: float = 1.0):
        self.running = True
        self.output_csv.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.output_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp", "elapsed_s", "system_cpu_pct", "system_ram_pct",
                "system_ram_used_mb", "proc_cpu_pct", "proc_ram_rss_mb",
                "proc_handles_fds", "net_bytes_sent", "net_bytes_recv"
            ])

            t0 = time.time()
            net_start = psutil.net_io_counters()

            while self.running and (time.time() - t0) < duration_seconds:
                t_now = time.time()
                elapsed = t_now - t0
                sys_cpu = psutil.cpu_percent(interval=None)
                sys_mem = psutil.virtual_memory()
                net_now = psutil.net_io_counters()

                proc_cpu = 0.0
                proc_rss = 0.0
                proc_handles = 0

                if self._target_proc and self._target_proc.is_running():
                    try:
                        proc_cpu = self._target_proc.cpu_percent(interval=None)
                        proc_mem = self._target_proc.memory_info()
                        proc_rss = proc_mem.rss / (1024 * 1024)
                        proc_handles = get_handles_or_fds(self._target_proc)
                    except Exception:
                        pass

                writer.writerow([
                    f"{t_now:.2f}", f"{elapsed:.1f}", sys_cpu, sys_mem.percent,
                    round(sys_mem.used / (1024 * 1024), 1), proc_cpu,
                    round(proc_rss, 1), proc_handles,
                    net_now.bytes_sent - net_start.bytes_sent,
                    net_now.bytes_recv - net_start.bytes_recv,
                ])
                f.flush()
                time.sleep(interval)

    def stop(self):
        self.running = False


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=str, required=True)
    parser.add_argument("--pid", type=int, default=None)
    parser.add_argument("--duration", type=float, default=60.0)
    args = parser.parse_args()

    mon = SystemMonitor(Path(args.out), target_pid=args.pid)
    mon.start_sampling(duration_seconds=args.duration)
