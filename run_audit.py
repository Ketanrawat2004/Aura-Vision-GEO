#!/usr/bin/env python3
"""
Convenience Root Runner for Aura-Vision-GEO.
Delegates directly to the designated entrypoint skill:
    skills/audit-orchestrator/scripts/run_audit.py

Usage:
    python run_audit.py --site https://example.com [--max-pages 12] [--out audit_report]
"""
import os
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENTRYPOINT_SCRIPT = os.path.join(BASE_DIR, "skills", "audit-orchestrator", "scripts", "run_audit.py")


def main():
    cmd = [sys.executable, ENTRYPOINT_SCRIPT] + sys.argv[1:]
    sys.exit(subprocess.run(cmd).returncode)


if __name__ == "__main__":
    main()
