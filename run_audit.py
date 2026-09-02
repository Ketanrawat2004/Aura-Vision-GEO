#!/usr/bin/env python3
"""
One-command convenience runner for the Aura-Vision-GEO Marketplace.
Dispatches all 5 worker skills and aggregates their findings into audit_report.json and audit_report.md.

Usage:
    python run_audit.py --site https://stripe.com [--pages https://stripe.com https://stripe.com/pricing] [--out audit_report]
"""
import argparse
import os
import subprocess
import sys
import tempfile

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


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

    print(f"================================================================")
    print(f"  Aura-Vision-GEO — Enterprise AI & GEO Audit Pipeline")
    print(f"  Auditing: {site_url}")
    print(f"  Pages:    {', '.join(pages)}")
    print(f"================================================================")

    with tempfile.TemporaryDirectory() as tmpdir:
        out_1 = os.path.join(tmpdir, "1_crawl.json")
        out_2 = os.path.join(tmpdir, "2_render.json")
        out_3 = os.path.join(tmpdir, "3_struct.json")
        out_4 = os.path.join(tmpdir, "4_freshness.json")
        out_5 = os.path.join(tmpdir, "5_engage.json")

        # 1. Crawlability
        print("[1/5] Running crawl-and-render-audit (robots.txt & sitemaps)...")
        cmd1 = [py_exec, os.path.join(BASE_DIR, "skills", "crawl-and-render-audit", "scripts", "check_crawlability.py"),
                "--site", site_url, "--pages"] + pages + ["--out", out_1]
        subprocess.run(cmd1, capture_output=True)

        # 2. Render Gap
        print("[2/5] Running crawl-and-render-audit (render gap)...")
        cmd2 = [py_exec, os.path.join(BASE_DIR, "skills", "crawl-and-render-audit", "scripts", "check_render_gap.py"),
                "--pages"] + pages + ["--out", out_2]
        subprocess.run(cmd2, capture_output=True)

        # 3. Structured Data
        print("[3/5] Running structured-fact-audit (JSON-LD & Microdata)...")
        cmd3 = [py_exec, os.path.join(BASE_DIR, "skills", "structured-fact-audit", "scripts", "check_structured_data.py"),
                "--pages"] + pages + ["--out", out_3]
        subprocess.run(cmd3, capture_output=True)

        # 4. Freshness
        print("[4/5] Running trust-and-corroboration-audit (freshness)...")
        cmd4 = [py_exec, os.path.join(BASE_DIR, "skills", "trust-and-corroboration-audit", "scripts", "check_freshness.py"),
                "--pages"] + pages + ["--out", out_4]
        subprocess.run(cmd4, capture_output=True)

        # 5. Engagement
        print("[5/5] Running engagement-audit (navigation, UX, dead links)...")
        cmd5 = [py_exec, os.path.join(BASE_DIR, "skills", "engagement-audit", "scripts", "check_engagement.py"),
                "--pages"] + pages + ["--out", out_5]
        subprocess.run(cmd5, capture_output=True)

        # 6. Aggregate
        print("[*] Aggregating findings into final audit report...")
        cmd_agg = [py_exec, os.path.join(BASE_DIR, "skills", "audit-orchestrator", "scripts", "aggregate_report.py"),
                   "--site", site_url, "--inputs", out_1, out_2, out_3, out_4, out_5, "--out", args.out]
        subprocess.run(cmd_agg)

    print(f"\nAudit complete! Deliverables generated:")
    print(f"  • JSON Report:     {args.out}.json")
    print(f"  • Markdown Report: {args.out}.md\n")


if __name__ == "__main__":
    main()
