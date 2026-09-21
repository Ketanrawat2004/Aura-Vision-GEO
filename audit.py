#!/usr/bin/env python3
"""
CLI Audit Runner for AuraVision GEO.
Runs the single-pass multi-page audit pipeline with clean terminal diagnostics.

Usage:
    python audit.py https://example.com
    python audit.py https://example.com --format json
    python audit.py https://example.com --max-pages 10
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

for folder in [
    ("audit-orchestrator", "scripts"),
    ("crawl-and-render-audit", "scripts"),
    ("structured-fact-audit", "scripts"),
    ("trust-and-corroboration-audit", "scripts"),
    ("engagement-audit", "scripts"),
]:
    skill_dir = os.path.join(BASE_DIR, "skills", folder[0], folder[1])
    if skill_dir not in sys.path:
        sys.path.insert(0, skill_dir)

import crawler  # type: ignore
import aggregate_report  # type: ignore
import check_crawlability  # type: ignore
import check_render_gap  # type: ignore
import check_structured_data  # type: ignore
import check_corroboration  # type: ignore
import check_freshness  # type: ignore
import check_engagement  # type: ignore
import check_empirical_search  # type: ignore

if hasattr(sys.stdout, "reconfigure"):
    try:
        getattr(sys.stdout, "reconfigure")(encoding="utf-8")
        getattr(sys.stderr, "reconfigure")(encoding="utf-8")
    except Exception:
        pass


def render_progress_bar(score: int, width: int = 20) -> str:
    clamped = max(0, min(100, score))
    filled = int((clamped / 100.0) * width)
    bar = "=" * filled + " " * (width - filled)
    return f"[{bar}] {clamped:>3}%"


def run_cli_audit(
    site_url: str,
    output_json: bool = False,
    max_pages: int = 12,
    out: str | None = None,
    empirical: bool = False,
    api_key: str | None = None
) -> dict:
    if out:
        for ext in (".json", ".md", ".html"):
            if out.lower().endswith(ext):
                out = out[:-len(ext)]
                break
    if not site_url:
        site_url = "https://example.com"
    site_url = str(site_url).strip()
    if not site_url.startswith("http://") and not site_url.startswith("https://"):
        site_url = "https://" + site_url

    start_time = time.perf_counter()

    if not output_json:
        print("=" * 65)
        print("  Aura-Vision-GEO — AI Discoverability & Retention Audit")
        print(f"  Target:    {site_url}")
        print(f"  Max Pages: {max_pages}")
        print("=" * 65)
        print("\n[1/3] Ingesting site via internal crawler (single-pass)...")

    # Step 1: Ingest via crawler (Single Pass)
    raw_crawled = crawler.crawl_website(site_url, max_pages=max_pages)
    valid_pages = [p for p in raw_crawled if p.get("status") == 200 and len(p.get("html", "").strip()) > 0]
    blocked_pages = [p for p in raw_crawled if p.get("status") != 200 or not p.get("html", "").strip()]

    if not valid_pages:
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
        elapsed = time.perf_counter() - start_time
        report["execution_seconds"] = round(elapsed, 3)

        if out:
            out_dir = os.path.dirname(os.path.abspath(f"{out}.json"))
            if out_dir:
                os.makedirs(out_dir, exist_ok=True)
            with open(f"{out}.json", "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            with open(f"{out}.md", "w", encoding="utf-8") as f:
                f.write(aggregate_report.render_markdown(report))
            with open(f"{out}.html", "w", encoding="utf-8") as f:
                f.write(aggregate_report.render_html(report))

        if output_json:
            print(json.dumps(report, indent=2, ensure_ascii=False))
            return report

        # Terminal Report Presentation
        s = report.get("summary", {})
        print("-" * 65)
        print(f"Overall Health Score:  N/A (Not Assessed)  |  Runtime: {elapsed:.2f}s")
        print(f"Summary: {s.get('total_findings', 1)} Finding(s) ({s.get('critical', 0)} Critical, {s.get('high', 0)} High, {s.get('medium', 0)} Medium, {s.get('low', 0)} Low)")
        print(f"Coverage Status:       NOT ACCESSIBLE ({classified['cause']}: {first_err})")
        print("-" * 65)

        print("\nDiagnostic Pillar Health:")
        print("  1. AI Crawler Access:        [Not Assessed - Route Inaccessible]")
        print("  2. DOM Hydration & Rendering: [Not Verified - Route Inaccessible]")
        print("  3. Structured Fact Graph:    [Not Verified - Route Inaccessible]")
        print("  4. Trust & Corroboration:    [Not Verified - Route Inaccessible]")
        print("  5. On-Site Visitor Retention: [Not Verified - Route Inaccessible]")

        print("\nKey Actionable Findings:")
        zf = report["findings"][0] if report.get("findings") else zero_finding
        sev = zf.get('severity', 'low').upper()
        conf = zf.get('confidence', 'high').upper()
        act_sum = zf.get('suggested_action', {}).get('summary', '') if isinstance(zf.get('suggested_action'), dict) else str(zf.get('suggested_action', ''))
        print(f"\n  [{sev} | CONFIDENCE: {conf}] {zf.get('id', 'F-001')}: {zf.get('title')}")
        print(f"    Evidence: {zf.get('evidence')}")
        print(f"    Action:   {act_sum}")

        print("\n" + "=" * 65 + "\n")
        return report

    pages = valid_pages
    extra_findings = []
    if blocked_pages:
        coverage = {
            "status": "partial",
            "reason": f"{len(valid_pages)} page(s) accessible, {len(blocked_pages)} route(s) restricted or inaccessible",
            "accessible_pages": len(valid_pages),
            "inaccessible_routes": len(blocked_pages),
            "verified": ["crawler_access", "machine_readability", "structured_data", "trust_and_corroboration", "on_site_engagement"],
            "not_verified": ["inaccessible_subroutes_content"],
            "not_accessible": [p.get("url", site_url) for p in blocked_pages[:5]]
        }
        extra_findings.append({
            "title": f"Audit coverage partial: {len(valid_pages)} page(s) evaluated, {len(blocked_pages)} route(s) restricted or inaccessible",
            "category": "discoverability",
            "subcategory": "crawlability",
            "impact": "cosmetic",
            "scope": "single-page",
            "confidence": "high",
            "evidence": f"Successfully evaluated {len(valid_pages)} page(s). Inaccessible or restricted routes: {[p.get('url', site_url) for p in blocked_pages[:3]]}.",
            "suggested_action": {
                "summary": "Ensure public informational routes are uniformly accessible to automated answer engine fetchers.",
                "priority": "low",
                "mechanism": "Partial crawler restrictions prevent answer engines from synthesizing comprehensive domain knowledge."
            }
        })
    else:
        coverage = {
            "status": "verified",
            "accessible_pages": len(valid_pages),
            "inaccessible_routes": 0,
            "verified": ["crawler_access", "machine_readability", "structured_data", "trust_and_corroboration", "on_site_engagement", "temporal_freshness"],
            "not_verified": [],
            "not_accessible": []
        }

    if not output_json:
        print(f"  Ingested {len(pages)} internal pages in {time.perf_counter() - start_time:.2f}s.")
        print("\n[2/3] Executing 5 diagnostic worker skills...")

    # Step 2: Worker skills
    f_crawl, o_crawl = check_crawlability.check_site(site_url, pages_data=pages)
    f_render, o_render = check_render_gap.check_pages_data(pages)
    f_struct, o_struct = check_structured_data.check_pages_data(pages)
    f_corrob, o_corrob = check_corroboration.audit_corroboration(pages, site_url)
    f_fresh, o_fresh = check_freshness.check_freshness(pages)
    f_engage, o_engage = check_engagement.check_pages_data(pages, site_url=site_url)
    emp_meta, f_emp, o_emp = check_empirical_search.audit_empirical_search(
        pages, site_url, enable_empirical=empirical, api_key=api_key
    )

    raw_findings = extra_findings + f_crawl + f_render + f_struct + f_corrob + f_fresh + f_engage + f_emp
    raw_opps = o_crawl + o_render + o_struct + o_corrob + o_fresh + o_engage + o_emp

    # Step 3: Deduplicate & Aggregate
    if not output_json:
        print("\n[3/3] Synthesizing audit report and calculating scores...")

    merged_findings = aggregate_report.dedupe(raw_findings)
    report = aggregate_report.build_report(
        site_url,
        merged_findings,
        raw_opps,
        crawled_pages_count=len(pages),
        coverage=coverage,
        empirical_corroboration=emp_meta
    )

    s = report["summary"]
    crit = s["critical"]
    high = s["high"]
    med = s["medium"]
    low = s["low"]

    score = report.get("score")
    grade = report.get("grade")

    elapsed = time.perf_counter() - start_time
    report["execution_seconds"] = round(elapsed, 3)

    if out:
        out_dir = os.path.dirname(os.path.abspath(f"{out}.json"))
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        with open(f"{out}.json", "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        with open(f"{out}.md", "w", encoding="utf-8") as f:
            f.write(aggregate_report.render_markdown(report))
        with open(f"{out}.html", "w", encoding="utf-8") as f:
            f.write(aggregate_report.render_html(report))

    if output_json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return report

    # Terminal Report Presentation
    cov = report.get("coverage", {})
    cov_status = cov.get("status", "verified").upper() if cov else "VERIFIED"
    cov_detail = f" ({cov.get('accessible_pages', len(valid_pages))} accessible / {cov.get('inaccessible_routes', 0)} restricted)" if cov_status == "PARTIAL" else ""
    print("-" * 65)
    if score is not None and grade is not None:
        print(f"Overall Health Score:  {score}/100 (Grade {grade})  |  Runtime: {elapsed:.2f}s")
    else:
        print(f"Overall Health Score:  N/A (Not Assessed)  |  Runtime: {elapsed:.2f}s")
    print(f"Summary: {s['total_findings']} Finding(s) ({crit} Critical, {high} High, {med} Medium, {low} Low)")
    print(f"Coverage Status:       {cov_status}{cov_detail}")
    print("-" * 65)

    # 5 Diagnostic Pillars
    def calc_pillar_score(subcats=None, cats=None):
        subcats = set(subcats or [])
        cats = set(cats or [])
        matching = [
            f for f in report.get("findings", [])
            if (f.get("subcategory") in subcats or f.get("category") in cats)
            and not (f.get("subcategory") == "crawlability" and "coverage partial" in f.get("title", "").lower())
        ]
        if not matching:
            return 100
        deduction = sum(
            30 if f.get("severity") == "critical"
            else 15 if f.get("severity") == "high"
            else 8 if f.get("severity") == "medium"
            else 3
            for f in matching
        )
        return max(10, min(100, 100 - deduction))

    p_crawl = calc_pillar_score(subcats=["crawlability"])
    p_render = calc_pillar_score(subcats=["render-gap"])
    p_struct = calc_pillar_score(subcats=["structured-data"])
    p_trust = calc_pillar_score(subcats=["trust"])
    p_engage = calc_pillar_score(cats=["engagement"], subcats=["engagement"])

    print("\nDiagnostic Pillar Health:")
    print(f"  1. AI Crawler Access:        {render_progress_bar(p_crawl)}")
    print(f"  2. DOM Hydration & Rendering: {render_progress_bar(p_render)}")
    print(f"  3. Structured Fact Graph:    {render_progress_bar(p_struct)}")
    print(f"  4. Trust & Corroboration:    {render_progress_bar(p_trust)}")
    print(f"  5. On-Site Visitor Retention: {render_progress_bar(p_engage)}")

    emp = report.get("empirical_corroboration", {})
    e_stat = emp.get("status", "not_run").upper()
    if e_stat == "COMPLETED":
        e_msg = f"VERIFIED (Domain confirmed via {emp.get('provider')})" if emp.get("matched") else f"UNVERIFIED (Domain absent from {emp.get('provider')})"
    elif e_stat == "ERROR":
        e_msg = f"ERROR ({emp.get('reason')})"
    else:
        e_msg = "NOT RUN (Optional - pass --empirical to run)"

    print("\nEmpirical External Grounding:")
    print(f"  • Brand Search Verification: [{e_msg}]")
    if emp.get("evidence"):
        print(f"    Evidence: {emp['evidence']}")

    print("\nKey Actionable Findings:")
    if not report["findings"]:
        print("  Zero defects detected across all 5 diagnostic pillars.")
    else:
        for idx, f in enumerate(report["findings"][:5], 1):
            act_sum = f.get('suggested_action', {}).get('summary', '') if isinstance(f.get('suggested_action'), dict) else str(f.get('suggested_action', ''))
            print(f"\n  [{f.get('severity', 'low').upper()}] {f.get('id', f'F-{idx:03d}')}: {f.get('title')}")
            print(f"    Evidence: {f.get('evidence')}")
            print(f"    Action:   {act_sum}")

        if len(report["findings"]) > 5:
            print(f"\n  ... and {len(report['findings']) - 5} more findings.")

    if out and not output_json:
        print(f"\nSaved deliverables: {out}.json, {out}.md, {out}.html")

    print("\n" + "=" * 65 + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description="AuraVision GEO Terminal CLI Auditor")
    parser.add_argument("site", nargs="?", default=None, help="Target site URL")
    parser.add_argument("--site", dest="site_flag", default=None, help="Target site URL (e.g. https://example.com)")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format (default: text)")
    parser.add_argument("--json", dest="json_flag", action="store_true", help="Output format as JSON (shorthand for --format json)")
    parser.add_argument("--max-pages", type=int, default=12, help="Max pages to crawl (default: 12)")
    parser.add_argument("--empirical", action="store_true", help="Enable live empirical search verification")
    parser.add_argument("--api-key", default=None, help="Optional search API key")
    parser.add_argument("--out", default=None, help="Optional output basename to write deliverables")
    args = parser.parse_args()

    target = args.site_flag or args.site or "https://example.com"
    is_json = (args.format == "json" or args.json_flag)
    return run_cli_audit(
        target,
        output_json=is_json,
        max_pages=args.max_pages,
        out=args.out,
        empirical=args.empirical,
        api_key=args.api_key
    )


if __name__ == "__main__":
    main()
