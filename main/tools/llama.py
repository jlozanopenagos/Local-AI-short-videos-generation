"""
tools/llama.py — CLI management utility for headless llama.cpp server.

Usage (from inside main/):
    py tools/llama.py start      # Starts llama-server headless in background
    py tools/llama.py stop       # Stops llama-server and releases VRAM
    py tools/llama.py restart    # Restarts llama-server
    py tools/llama.py status     # Shows current PID, port, status, model name
    py tools/llama.py logs       # Displays recent log output
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.llama_manager import get_llama_manager


def main():
    parser = argparse.ArgumentParser(
        description="LlamaServer Headless Supervisor CLI",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # start
    start_p = subparsers.add_parser("start", help="Start llama-server headless in background")
    start_p.add_argument("--timeout", type=int, default=60, help="Wait timeout in seconds (default: 60)")
    start_p.add_argument("--no-wait", action="store_true", help="Do not wait for server to become responsive")

    # stop
    subparsers.add_parser("stop", help="Stop running llama-server process and release VRAM")

    # restart
    restart_p = subparsers.add_parser("restart", help="Restart llama-server")
    restart_p.add_argument("--timeout", type=int, default=60, help="Wait timeout in seconds (default: 60)")

    # status
    subparsers.add_parser("status", help="Display current status and health of llama-server")

    # logs
    logs_p = subparsers.add_parser("logs", help="Display recent log lines")
    logs_p.add_argument("-n", "--lines", type=int, default=50, help="Number of lines to tail (default: 50)")

    args = parser.parse_args()
    mgr = get_llama_manager()

    if args.command == "start":
        ok = mgr.start(timeout=args.timeout, wait=not args.no_wait)
        sys.exit(0 if ok else 1)

    elif args.command == "stop":
        ok = mgr.stop()
        sys.exit(0 if ok else 1)

    elif args.command == "restart":
        ok = mgr.restart(timeout=args.timeout)
        sys.exit(0 if ok else 1)

    elif args.command == "status":
        info = mgr.get_status()
        status_icon = "🟢" if info["status"] == "ONLINE" else "🔴"
        print("\n" + "=" * 50)
        print("🦙 LLAMA.CPP (GEMMA) HEADLESS SERVICE STATUS")
        print("=" * 50)
        print(f"• Status:        {status_icon} {info['status']}")
        print(f"• Endpoint:      {info['api_url']}")
        print(f"• Port:          {info['port']}")
        print(f"• Model:         {info['model_name']}")
        print(f"• Process PID:   {info['pid'] or 'None (Not running)'}")
        print(f"• llama.cpp Dir: {info['llm_dir']}")
        print(f"• Log Location:  {info['log_file']}")
        print("=" * 50 + "\n")

    elif args.command == "logs":
        if not mgr.log_file.exists():
            print(f"Log file not found at {mgr.log_file}")
            sys.exit(1)
        with open(mgr.log_file, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
            for line in lines[-args.lines:]:
                sys.stdout.write(line)


if __name__ == "__main__":
    main()

