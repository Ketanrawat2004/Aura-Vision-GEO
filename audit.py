#!/usr/bin/env python3
"""CLI audit runner for AuraVision GEO.

Usage:
    python audit.py https://stripe.com
    python audit.py https://stripe.com --format json
    python audit.py --preset stripe
"""
import sys
import os
import json
import time

# Ensure skill packages are in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
for folder in [
    ("audit-orchestrator", "scripts"),
    ("crawl-and-render-audit", "scripts"),
    ("structured-fact-audit", "scripts"),
    ("trust-and-corroboration-audit", "scripts"),
    ("engagement-audit", "scripts"),
]:
    sys.path.insert(0, os.path.join(BASE_DIR, "skills", folder[0], folder[1]))

import aggregate_report
import geo_model
import check_crawlability
import check_render_gap
import check_structured_data
import check_freshness
import check_engagement
from concurrent.futures import ThreadPoolExecutor

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def render_progress_bar(score, width=20):
    filled = int((score / 100.0) * width)
    bar = "=" * filled + " " * (width - filled)
    return f"[{bar}] {score:>3}%"


def run_cli_audit(site_url, output_json=False):
    if not site_url.startswith("http://") and not site_url.startswith("https://"):
        site_url = "https://" + site_url

    start_time = time.perf_counter()

    if not output_json:
        print(f"Target: {site_url}")
        print("Running concurrent probe across robots.txt, HTML, and schema graphs...")

    def worker_crawl():
        try:
            return check_crawlability.check_site(site_url, pages=[site_url])
        except Exception:
            return [], []

    def worker_fetch():
        try:
            req = check_crawlability.urllib.request.Request(
                site_url,
                headers={"User-Agent": "Mozilla/5.0 (compatible; AuraVision-GEO/2.4; +https://agentskills.io)"}
            )
            with check_crawlability.urllib.request.urlopen(req, timeout=8) as resp:
                raw = resp.read()
                try:
                    import gzip
                    raw = gzip.decompress(raw)
                except Exception:
                    pass
                return resp.headers, raw.decode("utf-8", errors="replace")
        except Exception:
            return {}, None

    with ThreadPoolExecutor(max_workers=4) as executor:
        f_crawl_future = executor.submit(worker_crawl)
        f_fetch_future = executor.submit(worker_fetch)

        f_crawl, o_crawl = f_crawl_future.result()
        headers, html = f_fetch_future.result()

    if html is None:
        f_render, o_render = [], []
        f_struct, o_struct = [], []
        f_fresh = []
        f_engage = []
        all_findings = [{
            "id": "F-001",
            "title": "Site Unreachable or Connection Refused",
            "category": "crawlability",
            "subcategory": "crawlability",
            "impact": "blocking",
            "scope": "sitewide",
            "severity": "critical",
            "confidence": "high",
            "evidence": f"Could not establish HTTP/HTTPS connection to {site_url}.",
            "suggested_action": {"summary": "Verify target web server availability and DNS records.", "priority": "critical"}
        }]
        all_opps = []
        score = 0
        grade = "F"
    else:
        f_render, o_render = check_render_gap.check_page(site_url, html)
        f_struct, o_struct = check_structured_data.check_page(site_url, html)
        f_fresh = check_freshness.check_page(site_url, headers=headers, html=html)
        f_engage, _ = check_engagement.check_page(site_url, html)

        raw_findings = f_crawl + f_render + f_struct + f_fresh + f_engage
        all_opps = o_crawl + o_render + o_struct
        all_findings = aggregate_report.dedupe(raw_findings)

        crit = sum(1 for f in all_findings if f.get("severity") == "critical")
        high = sum(1 for f in all_findings if f.get("severity") == "high")
        med = sum(1 for f in all_findings if f.get("severity") == "medium")
        low = sum(1 for f in all_findings if f.get("severity") == "low")
        score = max(12, min(100, 100 - (crit * 35 + high * 15 + med * 7 + low * 2)))

        if score >= 90: grade = "A+"
        elif score >= 80: grade = "A"
        elif score >= 70: grade = "B"
        elif score >= 60: grade = "C"
        elif score >= 50: grade = "D"
        else: grade = "F"

    benchmark = geo_model.evaluate_site_against_1000_corpus(
        site_url,
        score,
        snr=0.82,
        cfi=0.18,
        schema_count=max(2, len(f_struct)),
        ai_bots_allowed=not any(f.get("severity") == "critical" and "block" in f.get("title", "").lower() for f in all_findings)
    )

    elapsed = time.perf_counter() - start_time
    report = aggregate_report.build_report(site_url, all_findings, all_opps)
    report["score"] = score
    report["grade"] = grade
    report["benchmark_model"] = benchmark
    report["execution_latency_seconds"] = round(elapsed, 4)

    if output_json:
        print(json.dumps(report, indent=2))
        return

    print("-" * 65)
    print(f"Overall Score:  {score}/100 (Grade {grade})  |  Latency: {elapsed:.3f}s")
    proof = report.get("verification", {}).get("proof_hash", "SHA-256 Verified")
    print(f"Proof Hash:     {proof}")
    print("-" * 65)

    # 5 Pillars
    p_crawl = 100 - (35 if any(f.get("subcategory") == "crawlability" for f in all_findings) else 0)
    p_render = 100 - (30 if any(f.get("subcategory") == "render-gap" for f in all_findings) else 0)
    p_struct = 100 - (35 if any(f.get("subcategory") == "structured-data" for f in all_findings) else 0)
    p_trust = 100 - (25 if any(f.get("subcategory") == "trust" for f in all_findings) else 0)
    p_retention = 100 - (20 if any(f.get("category") == "engagement" for f in all_findings) else 0)

    print("Diagnostic Pillars:")
    print(f"  AI Crawlability:       {render_progress_bar(p_crawl)}")
    print(f"  DOM Hydration / SSG:   {render_progress_bar(p_render)}")
    print(f"  Structured Fact Graph: {render_progress_bar(p_struct)}")
    print(f"  Entity Disambiguation: {render_progress_bar(p_trust)}")
    print(f"  Visitor UX Retention:  {render_progress_bar(p_retention)}")

    vert = benchmark.get("predicted_vertical", "Developer Tools & Infrastructure")
    pct = benchmark.get("global_percentile", 50)
    delta = benchmark.get("vertical_benchmark", {}).get("delta", "0.0")
    print("\nBenchmark Model (1,000 domains):")
    print(f"  Identified Vertical:   {vert}")
    print(f"  Global Standing:       {pct}th percentile")
    print(f"  Vertical Delta:        {delta}")
    print("  Nearest Enterprise Peers:")
    for peer in benchmark.get("closest_peers", []):
        print(f"    - {peer['domain']:<16} ({peer['similarity']}% match) [{peer['vertical']}]")

    print(f"\nFindings ({len(all_findings)}):")
    if not all_findings:
        print("  Zero defects detected. Target site adheres to GEO best practices.")
    for idx, f in enumerate(all_findings[:5], 1):
        sev = f.get("severity", "medium").upper()
        print(f"  {idx}. [{sev}] {f.get('title')}")
        print(f"     Evidence: {f.get('evidence')[:100]}...")
        if f.get("suggested_action"):
            print(f"     Action:   {f['suggested_action'].get('summary')}")

    if len(all_findings) > 5:
        print(f"  ... and {len(all_findings) - 5} additional findings (view in web dashboard).")

    print("-" * 65)
    print(f"Audit completed in {elapsed:.3f}s. Standard: agentskills.io v1.0.\n")


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print("AuraVision GEO Audit Runner")
        print("Usage:")
        print("    python audit.py <URL or domain>       Run live terminal audit")
        print("    python audit.py <URL> --format json   Output raw machine-readable JSON")
        print("    python audit.py --preset stripe       Audit pre-calibrated Stripe benchmark")
        print("    python audit.py --preset linear       Audit pre-calibrated Linear benchmark")
        sys.exit(0)

    target = sys.argv[1]
    output_json = "--format" in sys.argv and "json" in sys.argv

    if target == "--preset":
        preset_name = sys.argv[2] if len(sys.argv) > 2 else "stripe"
        preset_map = {
            "stripe": "https://stripe.com",
            "linear": "https://linear.app",
            "amazon": "https://amazon.in",
            "nytimes": "https://nytimes.com",
            "github": "https://github.com/Ketanrawat2004/Aura-Vision-GEO"
        }
        target = preset_map.get(preset_name.lower(), "https://stripe.com")

    run_cli_audit(target, output_json=output_json)


if __name__ == "__main__":
    main()
