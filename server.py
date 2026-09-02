#!/usr/bin/env python3
"""
Lightweight, dependency-free local web server for the AI Visibility Audit Dashboard.
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

                # Run full audit pipeline in temporary workspace
                with tempfile.TemporaryDirectory() as tmpdir:
                    out_1 = os.path.join(tmpdir, "1_crawl.json")
                    out_2 = os.path.join(tmpdir, "2_render.json")
                    out_3 = os.path.join(tmpdir, "3_struct.json")
                    out_4 = os.path.join(tmpdir, "4_freshness.json")
                    out_5 = os.path.join(tmpdir, "5_engage.json")
                    out_report = os.path.join(tmpdir, "report")

                    py_exec = sys.executable

                    # 1. Crawlability
                    cmd1 = [py_exec, os.path.join(BASE_DIR, "skills", "crawl-and-render-audit", "scripts", "check_crawlability.py"),
                            "--site", site_url, "--pages"] + pages + ["--out", out_1]
                    subprocess.run(cmd1, capture_output=True, timeout=25)

                    # 2. Render gap
                    cmd2 = [py_exec, os.path.join(BASE_DIR, "skills", "crawl-and-render-audit", "scripts", "check_render_gap.py"),
                            "--pages"] + pages + ["--out", out_2]
                    subprocess.run(cmd2, capture_output=True, timeout=25)

                    # 3. Structured data
                    cmd3 = [py_exec, os.path.join(BASE_DIR, "skills", "structured-fact-audit", "scripts", "check_structured_data.py"),
                            "--pages"] + pages + ["--out", out_3]
                    subprocess.run(cmd3, capture_output=True, timeout=25)

                    # 4. Freshness
                    cmd4 = [py_exec, os.path.join(BASE_DIR, "skills", "trust-and-corroboration-audit", "scripts", "check_freshness.py"),
                            "--pages"] + pages + ["--out", out_4]
                    subprocess.run(cmd4, capture_output=True, timeout=25)

                    # 5. Engagement
                    cmd5 = [py_exec, os.path.join(BASE_DIR, "skills", "engagement-audit", "scripts", "check_engagement.py"),
                            "--pages"] + pages + ["--out", out_5]
                    subprocess.run(cmd5, capture_output=True, timeout=25)

                    # 6. Aggregate
                    cmd_agg = [py_exec, os.path.join(BASE_DIR, "skills", "audit-orchestrator", "scripts", "aggregate_report.py"),
                               "--site", site_url, "--inputs", out_1, out_2, out_3, out_4, out_5, "--out", out_report]
                    subprocess.run(cmd_agg, capture_output=True, timeout=15)

                    report_json_path = f"{out_report}.json"
                    if os.path.exists(report_json_path):
                        with open(report_json_path, "r", encoding="utf-8") as f:
                            report_data = json.load(f)
                    else:
                        report_data = {
                            "site": site_url,
                            "summary": {"total_findings": 0, "critical": 0, "high": 0, "medium": 0, "low": 0},
                            "findings": [],
                            "opportunities": []
                        }

                response_bytes = json.dumps(report_data, ensure_ascii=False).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(response_bytes)))
                self.end_headers()
                self.wfile.write(response_bytes)

            except Exception as e:
                err_resp = json.dumps({"error": str(e)}).encode("utf-8")
                self.send_response(500)
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
        super().end_headers()


def main():
    parser = argparse.ArgumentParser(description="AI Visibility Audit Web Server")
    parser.add_argument("--port", type=int, default=PORT, help="Port to listen on (default: 8000)")
    args = parser.parse_args()

    server_address = ("", args.port)
    httpd = http.server.HTTPServer(server_address, AuditHandler)
    print(f"==================================================")
    print(f"  AI Visibility Audit Dashboard Server")
    print(f"  Listening at: http://127.0.0.1:{args.port}/")
    print(f"==================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer shutting down.")


if __name__ == "__main__":
    main()
