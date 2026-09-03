#!/usr/bin/env python3
"""
Orchestrator runner for the Aura-Vision-GEO Marketplace.
Dispatches all 4 worker skills and aggregates their findings into audit_report.json and audit_report.md.

Usage:
    python run_audit.py --site https://stripe.com [--pages https://stripe.com https://stripe.com/pricing] [--out audit_report]
"""
import argparse
import os
import subprocess
import sys
import tempfile

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Base directory is 3 levels up: skills/audit-orchestrator/scripts -> repo root
BASE_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))


def main():
    parser = argparse.ArgumentParser(description="Run the full Aura-Vision-GEO pipeline on a target website.")
    parser.add_argument("--site", required=True, help="Root website URL (e.g. https://stripe.com)")
    parser.add_argument("--pages", nargs="*", default=None, help="Specific page URLs to audit (defaults to root site)")
    parser.add_argument("--out", default="audit_report", help="Output basename (default: audit_report)")
    args = parser.parse_args()

    site_url = args.site.strip()
    if not site_url.startswith("http://") and not site_url.startswith("https://"):
        site_url = "https://" + site_url

    pages = args.pages if args.pages else [site_url]
    py_exec = sys.executable

    print(f"Auditing target: {site_url}")

    with tempfile.TemporaryDirectory() as tmpdir:
        out_1 = os.path.join(tmpdir, "1_crawl.json")
        out_2 = os.path.join(tmpdir, "2_render.json")
        out_3 = os.path.join(tmpdir, "3_struct.json")
        out_4 = os.path.join(tmpdir, "4_freshness.json")
        out_5 = os.path.join(tmpdir, "5_engage.json")

        # 1. Crawlability
        cmd1 = [py_exec, os.path.join(BASE_DIR, "skills", "crawl-and-render-audit", "scripts", "check_crawlability.py"),
                "--site", site_url, "--pages"] + pages + ["--out", out_1]
        subprocess.run(cmd1, capture_output=True)

        # 2. Render Gap
        cmd2 = [py_exec, os.path.join(BASE_DIR, "skills", "crawl-and-render-audit", "scripts", "check_render_gap.py"),
                "--pages"] + pages + ["--out", out_2]
        subprocess.run(cmd2, capture_output=True)

        # 3. Structured Data
        cmd3 = [py_exec, os.path.join(BASE_DIR, "skills", "structured-fact-audit", "scripts", "check_structured_data.py"),
                "--pages"] + pages + ["--out", out_3]
        subprocess.run(cmd3, capture_output=True)

        # 4. Freshness
        cmd4 = [py_exec, os.path.join(BASE_DIR, "skills", "trust-and-corroboration-audit", "scripts", "check_freshness.py"),
                "--pages"] + pages + ["--out", out_4]
        subprocess.run(cmd4, capture_output=True)

        # 5. Engagement
        cmd5 = [py_exec, os.path.join(BASE_DIR, "skills", "engagement-audit", "scripts", "check_engagement.py"),
                "--pages"] + pages + ["--out", out_5]
        subprocess.run(cmd5, capture_output=True)

        # Aggregate report
        inputs = [p for p in [out_1, out_2, out_3, out_4, out_5] if os.path.exists(p)]
        cmd_agg = [py_exec, os.path.join(BASE_DIR, "skills", "audit-orchestrator", "scripts", "aggregate_report.py"),
                   "--site", site_url, "--inputs"] + inputs + ["--out", args.out]
        subprocess.run(cmd_agg)

    print(f"Generated {args.out}.json and {args.out}.md successfully.")


if __name__ == "__main__":
    main()
