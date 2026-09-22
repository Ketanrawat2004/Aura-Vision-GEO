#!/usr/bin/env python3
"""
Designated Entrypoint Runner for the Aura-Vision-GEO Marketplace.
Implements the single-pass crawl-and-audit pipeline strictly conforming to the
Adobe University Hackathon 2026 Round 3 specification.

Architecture:
  URL
   ↓
  [1] Orchestrator internal crawler (robots.txt, same-origin, normalized, max 12 pages)
   ↓
  [2] Shared in-memory / temporary page dataset
   ↓
  [3] Worker skill audit dispatch (ZERO redundant HTTP fetching):
      • crawl-and-render-audit: check_crawlability.py & check_render_gap.py
      • structured-fact-audit:  check_structured_data.py
      • trust-and-corroboration: check_corroboration.py & check_freshness.py
      • engagement-audit:       check_engagement.py
   ↓
  [4] Orchestrator aggregation (aggregate_report.py)
   ↓
  [5] Single final audit report (JSON + Markdown)

Usage:
    python skills/audit-orchestrator/scripts/run_audit.py --site https://example.com [--max-pages 12] [--out audit_report]
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))

# Ensure crawler and aggregate_report are importable directly
sys.path.insert(0, SCRIPT_DIR)
import crawler
import aggregate_report

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Run the full single-pass Aura-Vision-GEO audit pipeline.")
    parser.add_argument("url", nargs="?", default=None, help="Root website URL to audit")
    parser.add_argument("--site", default=None, help="Root website URL to audit (e.g. https://stripe.com)")
    parser.add_argument("--max-pages", type=int, default=12, help="Max internal pages to crawl (default: 12)")
    parser.add_argument("--empirical", action="store_true", help="Enable optional live empirical search verification")
    parser.add_argument("--api-key", default=None, help="Optional search provider API key")
    parser.add_argument("--out", default="audit_report", help="Output basename (default: audit_report)")
    args = parser.parse_args()
    if args.out:
        for ext in (".json", ".md", ".html"):
            if args.out.lower().endswith(ext):
                args.out = args.out[:-len(ext)]
                break

    target = args.site or args.url
    if not target:
        parser.error("A target website URL is required (e.g. python run_audit.py https://example.com or --site https://example.com)")

    site_url = target.strip()
    if not site_url.startswith("http://") and not site_url.startswith("https://"):
        site_url = "https://" + site_url

    py_exec = sys.executable
    start_time = time.time()

    print("=" * 65, flush=True)
    print("  Aura-Vision-GEO — Agent Skill Marketplace Audit Pipeline", flush=True)
    print(f"  Target:     {site_url}", flush=True)
    print(f"  Max Pages:  {args.max_pages}", flush=True)
    print("=" * 65, flush=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        pages_json_path = os.path.join(tmpdir, "pages.json")

        # Step 1: Internal Crawl (Single Fetch Pass)
        print("\n[Phase 1/3] Crawling site with internal lightweight crawler...")
        crawled_pages = crawler.crawl_website(site_url, max_pages=args.max_pages)
        valid_pages = [p for p in crawled_pages if p.get("status") == 200 and len(p.get("html", "").strip()) > 0]
        blocked_pages = [p for p in crawled_pages if p.get("status") != 200 or not p.get("html", "").strip()]

        # ZERO ACCESS: Zero valid HTML pages could be retrieved
        if not valid_pages:
            print(f"  [Notice] Zero valid HTML pages could be crawled from {site_url}; generating access limitation diagnostic...", file=sys.stderr)
            first_err = blocked_pages[0].get("error", "Access restricted or connection failed") if blocked_pages else "Connection failed"
            status_code = blocked_pages[0].get("status", 0) if blocked_pages else 0

            classified = aggregate_report.classify_access_failure(status_code, first_err, site_url)
            zero_finding = classified["finding"]

            coverage = {
                "status": "not_accessible",
                "reason": f"Zero valid HTML pages retrieved ({classified['cause']}: {first_err})",
                "accessible_pages": 0,
                "inaccessible_routes": len(blocked_pages) if blocked_pages else 1,
                "verified": [],
                "not_verified": [
                    "machine_readability",
                    "structured_data",
                    "trust_and_corroboration",
                    "on_site_engagement",
                    "temporal_freshness"
                ],
                "not_accessible": [p.get("url", site_url) for p in blocked_pages[:5]] if blocked_pages else [site_url]
            }

            report = aggregate_report.build_report(site_url, [zero_finding], [], crawled_pages_count=0, coverage=coverage)
            out_dir = os.path.dirname(os.path.abspath(f"{args.out}.json"))
            if out_dir:
                os.makedirs(out_dir, exist_ok=True)
            with open(f"{args.out}.json", "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            with open(f"{args.out}.md", "w", encoding="utf-8") as f:
                f.write(aggregate_report.render_markdown(report))
            with open(f"{args.out}.html", "w", encoding="utf-8") as f:
                f.write(aggregate_report.render_html(report))

            elapsed = time.time() - start_time
            print(f"\nAudit complete in {elapsed:.2f}s! Generated deliverables:")
            print(f"  • Machine Report: {args.out}.json")
            print(f"  • Executive Brief: {args.out}.md")
            print(f"  • Interactive HTML: {args.out}.html\n")
            print_cli_summary(f"{args.out}.json")
            return

        # PARTIAL OR FULL ACCESS: Continue with valid pages
        print(f"  Successfully ingested {len(valid_pages)} page(s) ({len(blocked_pages)} blocked/restricted) in {time.time() - start_time:.2f}s (single-pass).")
        for idx, p in enumerate(valid_pages, 1):
            print(f"    {idx}. [{p.get('status')}] {p.get('url')} ({len(p.get('text', '').split())} words)")

        with open(pages_json_path, "w", encoding="utf-8") as f:
            json.dump(valid_pages, f, ensure_ascii=False)

        # Build coverage metadata
        coverage_json_path = os.path.join(tmpdir, "coverage.json")
        out_coverage = os.path.join(tmpdir, "0_coverage.json")
        extra_worker_outputs = []

        if blocked_pages:
            coverage = {
                "status": "partial",
                "reason": f"{len(valid_pages)} page(s) accessible, {len(blocked_pages)} route(s) restricted or inaccessible",
                "accessible_pages": len(valid_pages),
                "inaccessible_routes": len(blocked_pages),
                "verified": [
                    "crawler_access",
                    "machine_readability",
                    "structured_data",
                    "trust_and_corroboration",
                    "on_site_engagement"
                ],
                "not_verified": [
                    "inaccessible_subroutes_content"
                ],
                "not_accessible": [p["url"] for p in blocked_pages[:5]]
            }
            partial_finding = {
                "title": f"Audit coverage partial: {len(valid_pages)} page(s) evaluated, {len(blocked_pages)} route(s) restricted or inaccessible",
                "category": "discoverability",
                "subcategory": "crawlability",
                "impact": "cosmetic",
                "scope": "single-page",
                "confidence": "high",
                "evidence": f"Successfully evaluated {len(valid_pages)} page(s). Inaccessible or restricted routes: {[p['url'] for p in blocked_pages[:3]]}.",
                "suggested_action": {
                    "summary": "Ensure public informational routes are uniformly accessible to automated answer engine fetchers.",
                    "priority": "low",
                    "mechanism": "Partial crawler restrictions prevent answer engines from synthesizing comprehensive domain knowledge."
                }
            }
            with open(out_coverage, "w", encoding="utf-8") as f:
                json.dump({"findings": [partial_finding], "opportunities": []}, f, ensure_ascii=False)
            extra_worker_outputs.append(out_coverage)
        else:
            coverage = {
                "status": "verified",
                "accessible_pages": len(valid_pages),
                "inaccessible_routes": 0,
                "verified": [
                    "crawler_access",
                    "machine_readability",
                    "structured_data",
                    "trust_and_corroboration",
                    "on_site_engagement",
                    "temporal_freshness"
                ],
                "not_verified": [],
                "not_accessible": []
            }

        with open(coverage_json_path, "w", encoding="utf-8") as f:
            json.dump(coverage, f, ensure_ascii=False)

        # Step 2: Parallel/Sequential Worker Skill Ingestion (No Redundant Network Calls)
        print("\n[Phase 2/3] Dispatching worker skills against shared page dataset...", flush=True)

        out_crawl = os.path.join(tmpdir, "1_crawl.json")
        out_render = os.path.join(tmpdir, "2_render.json")
        out_struct = os.path.join(tmpdir, "3_struct.json")
        out_corrob = os.path.join(tmpdir, "4_corrob.json")
        out_fresh = os.path.join(tmpdir, "5_fresh.json")
        out_engage = os.path.join(tmpdir, "6_engage.json")
        out_empirical = os.path.join(tmpdir, "7_empirical.json")

        # 1. Crawlability
        print("  • Running crawl-and-render-audit (robots.txt, sitemaps, errors)...")
        cmd_crawl = [
            py_exec, os.path.join(BASE_DIR, "skills", "crawl-and-render-audit", "scripts", "check_crawlability.py"),
            "--site", site_url, "--pages-json", pages_json_path, "--out", out_crawl
        ]
        subprocess.run(cmd_crawl, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # 2. Render Gap
        print("  • Running crawl-and-render-audit (render gap & machine readability)...")
        cmd_render = [
            py_exec, os.path.join(BASE_DIR, "skills", "crawl-and-render-audit", "scripts", "check_render_gap.py"),
            "--pages-json", pages_json_path, "--out", out_render
        ]
        subprocess.run(cmd_render, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # 3. Structured Data
        print("  • Running structured-fact-audit (Schema.org, conflicts, non-text facts)...")
        cmd_struct = [
            py_exec, os.path.join(BASE_DIR, "skills", "structured-fact-audit", "scripts", "check_structured_data.py"),
            "--pages-json", pages_json_path, "--out", out_struct
        ]
        subprocess.run(cmd_struct, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # 4. Corroboration & Entity Collision
        print("  • Running trust-and-corroboration-audit (entity disambiguation & grounding)...")
        cmd_corrob = [
            py_exec, os.path.join(BASE_DIR, "skills", "trust-and-corroboration-audit", "scripts", "check_corroboration.py"),
            "--site", site_url, "--pages-json", pages_json_path, "--out", out_corrob
        ]
        subprocess.run(cmd_corrob, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # 5. Freshness
        print("  • Running trust-and-corroboration-audit (cross-page date consistency)...")
        cmd_fresh = [
            py_exec, os.path.join(BASE_DIR, "skills", "trust-and-corroboration-audit", "scripts", "check_freshness.py"),
            "--pages-json", pages_json_path, "--out", out_fresh
        ]
        subprocess.run(cmd_fresh, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # 6. Engagement
        print("  • Running engagement-audit (orientation, CTA, navigation, scannability)...")
        cmd_engage = [
            py_exec, os.path.join(BASE_DIR, "skills", "engagement-audit", "scripts", "check_engagement.py"),
            "--pages-json", pages_json_path, "--out", out_engage
        ]
        subprocess.run(cmd_engage, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # 7. Empirical Search Grounding (Optional)
        emp_label = "live external search validation" if args.empirical else "offline / unconfigured status"
        print(f"  • Running trust-and-corroboration-audit ({emp_label})...")
        cmd_empirical = [
            py_exec, os.path.join(BASE_DIR, "skills", "trust-and-corroboration-audit", "scripts", "check_empirical_search.py"),
            "--site", site_url, "--pages-json", pages_json_path, "--out", out_empirical
        ]
        if args.empirical:
            cmd_empirical.append("--empirical")
        if args.api_key:
            cmd_empirical.extend(["--api-key", args.api_key])
        subprocess.run(cmd_empirical, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Step 3: Synthesis & Deduplication
        print("\n[Phase 3/3] Synthesizing audit report with deduplication...", flush=True)
        worker_outputs = extra_worker_outputs + [out_crawl, out_render, out_struct, out_corrob, out_fresh, out_engage, out_empirical]
        cmd_agg = [
            py_exec, os.path.join(SCRIPT_DIR, "aggregate_report.py"),
            "--site", site_url,
            "--inputs"
        ] + worker_outputs + [
            "--out", args.out,
            "--pages-count", str(len(valid_pages)),
            "--coverage-json", coverage_json_path
        ]
        subprocess.run(cmd_agg, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    elapsed = time.time() - start_time
    print(f"\nAudit complete in {elapsed:.2f}s! Generated deliverables:")
    print(f"  • Machine Report: {args.out}.json")
    print(f"  • Executive Brief: {args.out}.md")
    print(f"  • Interactive HTML: {args.out}.html\n")

    print_cli_summary(f"{args.out}.json")


def print_cli_summary(report_json_path):
    try:
        with open(report_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        s = data.get("summary", {})
        findings = data.get("findings", [])
        crawled = data.get("crawled_pages", 1)

        score = data.get("score")
        grade = data.get("grade")
        cov = data.get("coverage", {})
        cov_status = cov.get("status", "verified").upper() if cov else "VERIFIED"

        print("=" * 70)
        print(f"  AuraVision GEO — Audit Summary: {data.get('site')}")
        print(f"  Pages Evaluated: {crawled} (Single-Pass Ingestion)")
        if score is not None and grade is not None:
            print(f"  Overall Score:   {score}/100 (Grade {grade})  |  Coverage: {cov_status}")
        else:
            print(f"  Overall Score:   N/A (Not Assessed)  |  Coverage: {cov_status}")
        print("=" * 70)
        print(f"  TOTAL FINDINGS: {s.get('total_findings', 0)}  |  CRITICAL: {s.get('critical', 0)}  |  HIGH: {s.get('high', 0)}  |  MEDIUM: {s.get('medium', 0)}  |  LOW: {s.get('low', 0)}")
        emp = data.get("empirical_corroboration", {})
        e_stat = emp.get("status", "not_run").upper()
        if e_stat == "COMPLETED":
            e_str = f"VERIFIED ({emp.get('provider')})" if emp.get("matched") else f"UNVERIFIED ({emp.get('provider')})"
        elif e_stat == "ERROR":
            e_str = "ERROR"
        else:
            e_str = "NOT RUN (pass --empirical to enable)"
        print(f"  EMPIRICAL GROUNDING: {e_str}")
        print("-" * 70)
        if not findings:
            print("  [CLEAN] No architectural defects detected across all 5 pillars.")
        else:
            for i, f in enumerate(findings[:6], 1):
                sev = f.get('severity', 'low').upper()
                print(f"  {i}. [{sev:<8}] {f.get('title')[:55]}")
            if len(findings) > 6:
                print(f"     ... and {len(findings) - 6} additional finding(s)")
        print("=" * 70 + "\n")
    except Exception:
        pass


if __name__ == "__main__":
    main()
