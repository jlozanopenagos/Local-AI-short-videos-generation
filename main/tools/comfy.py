"""
tools/comfy.py — CLI Command Interface for Headless ComfyUI Supervisor.

Usage:
    py tools/comfy.py start        # Boots ComfyUI headless in background (zero terminal windows)
    py tools/comfy.py stop         # Stops ComfyUI process cleanly
    py tools/comfy.py restart      # Stops and starts fresh
    py tools/comfy.py status       # Shows PID, port, VRAM, and queue statistics
    py tools/comfy.py logs         # Displays recent runtime logs
    py tools/comfy.py logs -f      # Follows live logs in real time (Ctrl+C to exit)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Configure UTF-8 console output for Windows
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.comfy_manager import ComfyManager


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Headless ComfyUI Process Supervisor & CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Start
    start_p = subparsers.add_parser("start", help="Start ComfyUI headless in the background")
    start_p.add_argument("--timeout", type=int, default=60, help="Seconds to wait for server initialization (default: 60)")
    start_p.add_argument("--no-wait", action="store_true", help="Launch without waiting for health probe")

    # Stop
    stop_p = subparsers.add_parser("stop", help="Stop ComfyUI process cleanly")
    stop_p.add_argument("--timeout", type=int, default=15, help="Seconds to wait for port release (default: 15)")

    # Restart
    restart_p = subparsers.add_parser("restart", help="Restart ComfyUI")
    restart_p.add_argument("--timeout", type=int, default=60, help="Seconds to wait for initialization (default: 60)")

    # Status
    subparsers.add_parser("status", help="Check status, PID, VRAM, and queue metrics")

    # Logs
    logs_p = subparsers.add_parser("logs", help="View ComfyUI logs")
    logs_p.add_argument("-f", "--follow", action="store_true", help="Follow live log output")
    logs_p.add_argument("-n", "--lines", type=int, default=50, help="Number of lines to show (default: 50)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    mgr = ComfyManager()

    if args.command == "start":
        ok = mgr.start(timeout=args.timeout, wait=not args.no_wait)
        return 0 if ok else 1

    elif args.command == "stop":
        ok = mgr.stop(timeout=args.timeout)
        return 0 if ok else 1

    elif args.command == "restart":
        ok = mgr.restart(timeout=args.timeout)
        return 0 if ok else 1

    elif args.command == "status":
        st = mgr.get_status()
        print("\n" + "=" * 50)
        print("🤖 COMFYUI HEADLESS SERVICE STATUS")
        print("=" * 50)
        print(f"• Status:        {'🟢 ONLINE' if st['online'] else '🔴 OFFLINE'}")
        print(f"• Endpoint:      {st['url']}")
        print(f"• Port:          {st['port']}")
        print(f"• Process PID:   {st['pid'] or 'None (Not running)'}")
        print(f"• Log Location:  {st['log_file']}")

        if st["system_stats"]:
            devs = st["system_stats"].get("devices", [])
            if devs:
                dev = devs[0]
                name = dev.get("name", "Unknown GPU")
                vram_total = round(dev.get("vram_total", 0) / (1024**3), 2)
                vram_free = round(dev.get("vram_free", 0) / (1024**3), 2)
                vram_used = round(vram_total - vram_free, 2)
                print(f"• Active GPU:    {name}")
                print(f"• VRAM Usage:    {vram_used} GB / {vram_total} GB ({vram_free} GB free)")

        if st["queue_stats"]:
            q = st["queue_stats"]
            print(f"• Active Queue:  {q['running']} running, {q['pending']} pending")

        print("=" * 50 + "\n")
        return 0

    elif args.command == "logs":
        mgr.tail_logs(lines=args.lines, follow=args.follow)
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())

