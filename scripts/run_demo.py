"""
scripts.run_demo
-----------------
Unified Competition Demo Launcher for IBVAP (Phase 11 / M12).

Launches the complete end-to-end intelligent border surveillance platform:
1. Command Center FastAPI Backend (:8000)
2. React Command Center Dashboard (:5173)
3. Edge AI Processing Node (multi-camera / simulated video stream)

Usage:
    python scripts/run_demo.py
    python scripts/run_demo.py --edge-config configs/phase1_default.yaml
    python scripts/run_demo.py --backend-only
"""

import argparse
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

# ANSI Colors
GREEN = "\033[92m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"


def print_banner():
    print(f"""
{CYAN}{BOLD}======================================================================
     IBVAP — Intelligent Border Video Analytics Platform
     Smart India Hackathon (SIH 2026) — Final Competition Build
======================================================================{RESET}
""")


def main():
    parser = argparse.ArgumentParser(description="IBVAP Unified Demo Launcher")
    parser.add_argument(
        "--edge-config",
        default="configs/phase1_default.yaml",
        help="Path to edge configuration YAML file.",
    )
    parser.add_argument(
        "--no-dashboard",
        action="store_true",
        help="Do not launch Vite React frontend dashboard.",
    )
    parser.add_argument(
        "--no-edge",
        action="store_true",
        help="Do not launch Edge AI node.",
    )
    args = parser.parse_args()

    print_banner()

    python_bin = sys.executable
    processes = []

    def cleanup_processes(signum=None, frame=None):
        print(f"\n{YELLOW}[SHUTDOWN] Terminating all IBVAP subsystem processes...{RESET}")
        for p in processes:
            try:
                p.terminate()
                p.wait(timeout=2.0)
            except Exception:
                p.kill()
        print(f"{GREEN}[SHUTDOWN] All services stopped cleanly.{RESET}")
        sys.exit(0)

    signal.signal(signal.SIGINT, cleanup_processes)
    signal.signal(signal.SIGTERM, cleanup_processes)

    try:
        # 1. Start FastAPI Backend
        print(f"{CYAN}[1/3] Starting Command Center Backend (FastAPI :8000)...{RESET}")
        backend_cmd = [
            python_bin,
            "-m",
            "uvicorn",
            "apps.backend.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
            "--log-level",
            "info",
        ]
        p_backend = subprocess.Popen(backend_cmd, cwd=str(ROOT_DIR))
        processes.append(p_backend)
        time.sleep(1.5)

        # 2. Start Dashboard
        if not args.no_dashboard:
            dashboard_dir = ROOT_DIR / "apps" / "dashboard"
            if (dashboard_dir / "package.json").exists():
                print(f"{CYAN}[2/3] Starting React Command Center Dashboard (:5173)...{RESET}")
                dash_cmd = ["npm", "run", "dev", "--", "--host"]
                p_dash = subprocess.Popen(dash_cmd, cwd=str(dashboard_dir))
                processes.append(p_dash)
                time.sleep(1.5)
            else:
                print(f"{YELLOW}[2/3] Skipping Dashboard (directory not found).{RESET}")

        # 3. Start Edge AI Node
        if not args.no_edge:
            print(
                f"{CYAN}[3/3] Starting Edge AI Processing Node (config: {args.edge_config})...{RESET}"
            )
            edge_cmd = [
                python_bin,
                "-m",
                "apps.edge.main",
                "--config",
                args.edge_config,
                "--no-display",
                "--stream-port",
                "8081",
            ]
            p_edge = subprocess.Popen(edge_cmd, cwd=str(ROOT_DIR))
            processes.append(p_edge)

        print(f"""
{GREEN}{BOLD}======================================================================
  All IBVAP subsystems are running!
  - Command Center UI:  http://localhost:5173
  - Backend API:        http://localhost:8000/docs
  - WebSocket Stream:   ws://localhost:8000/ws
  Press Ctrl+C at any time to stop all services.
======================================================================{RESET}
""")

        # Monitor loop
        while True:
            for p in processes:
                ret = p.poll()
                if ret is not None and ret != 0:
                    print(
                        f"{RED}[ERROR] Process {p.args} exited unexpectedly with code {ret}.{RESET}"
                    )
            time.sleep(1.0)

    except KeyboardInterrupt:
        cleanup_processes()


if __name__ == "__main__":
    main()
