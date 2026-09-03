#!/usr/bin/env python3
"""
Lightweight, dependency-free local web server for the Aura-Vision-GEO Dashboard.
Serves the web UI and provides a live POST /api/audit endpoint executing the marketplace skills.

Usage:
    python server.py [--port 8000]
"""
import argparse
import http.server
import json
import os
import subprocess
import sys
import tempfile
import urllib.parse

PORT = 8000
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(BASE_DIR, "web")


# Add skill script directories to Python path for direct in-memory execution
sys.path.insert(0, os.path.join(BASE_DIR, "skills", "crawl-and-render-audit", "scripts"))
sys.path.insert(0, os.path.join(BASE_DIR, "skills", "structured-fact-audit", "scripts"))
sys.path.insert(0, os.path.join(BASE_DIR, "skills", "trust-and-corroboration-audit", "scripts"))
sys.path.insert(0, os.path.join(BASE_DIR, "skills", "engagement-audit", "scripts"))
sys.path.insert(0, os.path.join(BASE_DIR, "skills", "audit-orchestrator", "scripts"))

import ssl
import urllib.request
import check_crawlability as c_crawl
import check_render_gap as c_render
import check_structured_data as c_struct
import check_freshness as c_fresh
import check_engagement as c_engage
import aggregate_report as c_agg


def run_fast_audit(site_url, pages):
    """Executes the full 5-skill GEO audit in memory with zero redundant fetches."""
    if not site_url.startswith("http://") and not site_url.startswith("https://"):
        site_url = "https://" + site_url

    if not pages:
        pages = [site_url]

    f_crawl, o_crawl = [], []
    f_render, o_render = [], []
    f_struct, o_struct = [], []
    f_fresh = []
    f_engage = []

    # 1. Crawlability & robots.txt / llms.txt
    try:
        sample_paths = [urllib.parse.urlparse(p).path or "/" for p in pages]
        f1, o1 = c_crawl.check_robots(site_url, sample_paths)
        f_crawl.extend(f1)
        o_crawl.extend(o1)
    except Exception as e:
        print(f"[Audit] Robots check warning: {e}", file=sys.stderr)

    # 2. Fetch pages and analyze content
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    fetched_at_least_one = False
    first_page_headers = {}
    first_page_html = None

    for p_url in pages[:4]:
        try:
            req = urllib.request.Request(p_url, headers={
                "User-Agent": "Aura-Vision-GEO/1.0 (+read-only site audit; respects robots.txt)",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5"
            })
            with urllib.request.urlopen(req, timeout=5, context=ctx) as resp:
                raw_bytes = resp.read()
                resp_headers = dict(resp.getheaders())
                if raw_bytes.startswith(b"\x1f\x8b") or p_url.endswith(".gz"):
                    import gzip
                    try:
                        raw_bytes = gzip.decompress(raw_bytes)
                    except Exception:
                        pass
                html = raw_bytes.decode("utf-8", errors="replace")
                fetched_at_least_one = True

                if first_page_html is None:
                    first_page_headers = resp_headers
                    first_page_html = html

                # Render Gap analysis
                r_f, r_o = c_render.check_page(p_url, html)
                f_render.extend(r_f)
                o_render.extend(r_o)

                # Structured Data / Schema analysis
                s_f, s_o = c_struct.check_page(p_url, html)
                f_struct.extend(s_f)
                o_struct.extend(s_o)

                # Engagement / Retention heuristics
                e_f, _ = c_engage.check_page(p_url, html)
                f_engage.extend(e_f)

        except Exception as e:
            print(f"[Audit] Page fetch warning for {p_url}: {e}", file=sys.stderr)

    # 3. Freshness checks (reuse pre-fetched HTML to avoid redundant HTTP round-trip)
    try:
        if first_page_html is not None:
            f_fresh = c_fresh.check_page(site_url, headers=first_page_headers, html=first_page_html)
        else:
            f_fresh = c_fresh.check_page(site_url)
    except Exception as e:
        print(f"[Audit] Freshness check warning: {e}", file=sys.stderr)

    # If domain completely failed to resolve / connection refused
    if not fetched_at_least_one and not f_crawl:
        all_findings = [{
            "title": "Site Unreachable or Host Connection Refused",
            "category": "crawlability",
            "subcategory": "crawlability",
            "impact": "blocking",
            "scope": "sitewide",
            "confidence": "high",
            "evidence": f"Could not establish HTTP/HTTPS connection to {site_url}. Verify server availability and DNS resolution.",
            "suggested_action": {
                "summary": "Ensure the target web server is live and accepting incoming public requests.",
                "priority": "critical"
            }
        }]
        all_opps = [{
            "title": "Enable HTTPS and Verify DNS A/AAAA Records",
            "suggested_action": {
                "summary": "Check DNS propagation and ensure SSL certificates are valid and responsive.",
                "priority": "critical"
            }
        }]
    else:
        all_findings = f_crawl + f_render + f_struct + f_fresh + f_engage
        all_opps = o_crawl + o_render + o_struct

    deduped = c_agg.dedupe(all_findings)
    report = c_agg.build_report(site_url, deduped, all_opps)
    if not fetched_at_least_one and not f_crawl:
        report["is_unreachable"] = True
        report["score"] = 0
        report["grade"] = "F"
        report["status"] = "Site Offline / Connection Refused"
        if "summary" in report:
            report["summary"]["is_unreachable"] = True
    return report


class AuditHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def do_POST(self):
        if self.path == "/api/audit":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body.decode("utf-8"))
                site_url = data.get("site", "").strip()
                if not site_url:
                    self.send_error(400, "Missing site URL")
                    return

                # Normalize URL
                if not site_url.startswith("http://") and not site_url.startswith("https://"):
                    site_url = "https://" + site_url

                pages = data.get("pages", [site_url])
                if not pages:
                    pages = [site_url]

                print(f"[API] Auditing target site: {site_url} ({len(pages)} page(s))...", flush=True)
                report_data = run_fast_audit(site_url, pages)

                response_bytes = json.dumps(report_data, ensure_ascii=False).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(response_bytes)))
                self.end_headers()
                self.wfile.write(response_bytes)

            except Exception as e:
                import traceback
                traceback.print_exc()
                # Return a valid fallback report for the site rather than breaking
                fallback = {
                    "site": site_url if 'site_url' in locals() else "https://example.com",
                    "audited_at": "2026-09-02T19:00:00Z",
                    "summary": {"total_findings": 1, "critical": 0, "high": 1, "medium": 0, "low": 0},
                    "findings": [{
                        "id": "F-001",
                        "title": "Audit Pipeline Timeout / Inspection Incomplete",
                        "severity": "high",
                        "category": "crawlability",
                        "confidence": "high",
                        "evidence": f"Inspection encountered error: {str(e)}",
                        "suggested_action": {"summary": "Retry with a direct canonical root URL.", "priority": "medium"}
                    }],
                    "opportunities": []
                }
                err_resp = json.dumps(fallback).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(err_resp)))
                self.end_headers()
                self.wfile.write(err_resp)
        else:
            self.send_error(404, "Endpoint not found")

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()


def main():
    parser = argparse.ArgumentParser(description="Aura-Vision-GEO Web Server")
    parser.add_argument("--port", type=int, default=PORT, help="Port to listen on (default: 8000)")
    args = parser.parse_args()

    server_address = ("", args.port)
    httpd = getattr(http.server, "ThreadingHTTPServer", http.server.HTTPServer)(server_address, AuditHandler)
    print(f"==================================================")
    print(f"  Aura-Vision-GEO Dashboard Server")
    print(f"  Listening at: http://127.0.0.1:{args.port}/")
    print(f"==================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer shutting down.")


if __name__ == "__main__":
    main()
