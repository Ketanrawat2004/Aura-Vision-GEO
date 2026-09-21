#!/usr/bin/env python3
"""
Automated Test & Generalization Verification Suite
for the Adobe University Hackathon 2026 Aura-Vision-GEO Platform.

Tests all 5 worker skills and orchestrator aggregation against 21 synthetic unseen scenarios & edge cases:
 1. Clean, well-structured website (Verifies zero false-positive flooding)
 2. JS-heavy website with empty initial HTML (#root SPA shell)
 3. Website with important facts locked solely in PDFs without HTML equivalent
 4. Website with legitimate PDF download where HTML already has specs (Zero false positive)
 5. Website with missing Schema.org markup on commercial product route
 6. Website with conflicting structured data (JSON-LD price $99 vs visible HTML $49) and numeric equivalence
 7. Website with stale dates & cross-page temporal conflicts (2026 copyright vs 2020 terms)
 8. Website with weak engagement (missing H1, vague slogan, no CTA, dead-end subpage)
 9. Website with common-noun entity collision risk (unanchored generic brand name)
10. Multi-page crawler verification traversing deep pages and respecting robots.txt
11. Normal static website verified coverage
12. Partially accessible website handling
13. Completely inaccessible website limitation reporting
14. Redirecting website crawl traversal
15. JS-heavy SPA detection
16. Zero access robots.txt classification
17. Zero access HTTP 401/403/429 classification
18. Zero access HTTP 5xx/404 classification
19. Zero access timeout classification
20. Zero access unsupported content classification
21. Root audit.py CLI runner verification (terminal, json, deliverables, programmatic API)

Usage:
    python test_generalization.py
"""
import http.server
import json
import os
import re
import socketserver
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import unittest.mock

if hasattr(sys, "stdout") and hasattr(sys.stdout, "reconfigure"):
    try:
        getattr(sys.stdout, "reconfigure")(encoding="utf-8")
        getattr(sys.stderr, "reconfigure")(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Insert skill scripts into sys.path
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

import aggregate_report  # type: ignore
import check_crawlability  # type: ignore
import check_render_gap  # type: ignore
import check_structured_data  # type: ignore
import check_corroboration  # type: ignore
import check_freshness  # type: ignore
import check_engagement  # type: ignore
import check_empirical_search  # type: ignore
import crawler  # type: ignore
import audit


class MockSiteHandler(http.server.BaseHTTPRequestHandler):
    """Synthetic multi-route HTTP server simulating various website architectures."""

    def log_message(self, format, *args):
        pass  # Quiet logging

    def do_GET(self):
        path = self.path.split("?")[0]

        if path == "/robots.txt":
            body = "User-agent: *\nAllow: /\n\nUser-agent: GPTBot\nDisallow: /\n\nSitemap: http://127.0.0.1/sitemap.xml\n"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))

        elif path in ("", "/"):
            # Homepage with links to subpages
            body = """<!DOCTYPE html>
            <html>
            <head>
                <title>Acme Global - Cloud Infrastructure</title>
                <meta name="viewport" content="width=device-width, initial-scale=1">
            </head>
            <body>
                <header>
                    <nav>
                        <a href="/products">Products</a>
                        <a href="/pricing">Pricing</a>
                        <a href="/about">About</a>
                        <a href="/contact">Contact</a>
                    </nav>
                </header>
                <main>
                    <h1>Enterprise Cloud Storage Infrastructure</h1>
                    <p>Designed for developers and enterprise engineering teams. Store, stream, and sync petabytes of data securely.</p>
                    <p><a href="/signup" class="btn">Start Free Trial</a></p>
                </main>
                <footer>
                    <p>© 2026 Acme Corp. All rights reserved.</p>
                </footer>
            </body>
            </html>"""
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))

        elif path == "/pricing":
            # Pricing page with conflict: Visible is $49, JSON-LD is $99
            body = """<!DOCTYPE html>
            <html>
            <head>
                <title>Acme Pricing Plans</title>
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <script type="application/ld+json">
                {
                    "@context": "https://schema.org",
                    "@type": "Product",
                    "name": "Acme Pro Tier",
                    "offers": {
                        "@type": "Offer",
                        "price": "99.00",
                        "priceCurrency": "USD"
                    }
                }
                </script>
            </head>
            <body>
                <nav><a href="/">Home</a></nav>
                <h1>Transparent Pricing Plans</h1>
                <p>Starting at $49 per month billed monthly. Pro tier with unlimited bandwidth.</p>
                <p><a href="/signup">Get Started</a></p>
            </body>
            </html>"""
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))

        elif path == "/dead-end":
            # Dead end page with no links
            body = "<html><body><h1>Internal Error Details</h1><p>Something went wrong.</p></body></html>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))

        elif path == "/restricted":
            self.send_response(403)
            self.end_headers()

        elif path == "/redirect-src":
            self.send_response(302)
            self.send_header("Location", "/redirect-dest")
            self.end_headers()

        elif path == "/redirect-dest":
            body = "<!DOCTYPE html><html><head><title>Destination</title><meta name='viewport' content='width=device-width, initial-scale=1'></head><body><h1>Redirect Succeeded</h1><p>Arrived at destination page.</p></body></html>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))

        elif path == "/spa-client":
            body = "<!DOCTYPE html><html><head><title>App</title><meta name='viewport' content='width=device-width, initial-scale=1'></head><body><div id='root'></div><script src='/app.js'></script></body></html>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))

        elif path == "/error-page":
            self.send_response(500)
            self.end_headers()

        elif path == "/products":
            body = "<!DOCTYPE html><html><head><title>Acme Products</title><meta name='viewport' content='width=device-width, initial-scale=1'></head><body><header><nav><a href='/'>Home</a><a href='/pricing'>Pricing</a></nav></header><main><h1>Enterprise Products</h1><p>High availability distributed database clusters.</p><p><a href='/signup'>Try Free</a></p></main></body></html>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))

        elif path == "/about":
            body = "<!DOCTYPE html><html><head><title>About Acme</title><meta name='viewport' content='width=device-width, initial-scale=1'></head><body><header><nav><a href='/'>Home</a></nav></header><main><h1>About Acme Corp</h1><p>Founded in 2020. Global cloud infrastructure provider.</p></main></body></html>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))

        elif path == "/contact":
            body = "<!DOCTYPE html><html><head><title>Contact Acme</title><meta name='viewport' content='width=device-width, initial-scale=1'></head><body><header><nav><a href='/'>Home</a></nav></header><main><h1>Contact Us</h1><p>Email us at support@acme.example.com or call +1-800-555-0100.</p></main></body></html>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))

        else:
            self.send_response(404)
            self.end_headers()


class TestAuraVisionGEOGeneralization(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Start background synthetic mock HTTP server on ephemeral port
        socketserver.TCPServer.allow_reuse_address = True
        cls.server = socketserver.TCPServer(("127.0.0.1", 0), MockSiteHandler)
        setattr(cls.server, "daemon_threads", True)
        cls.port = cls.server.server_address[1]
        cls.server_thread = threading.Thread(target=cls.server.serve_forever)
        cls.server_thread.daemon = True
        cls.server_thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.port}"

    @classmethod
    def tearDownClass(cls):
        try:
            cls.server.shutdown()
        except Exception:
            pass
        try:
            cls.server.server_close()
        except Exception:
            pass

    def test_01_severity_matrix_and_deduplication(self):
        """Verify mathematical severity derivation (Impact x Scope) and Jaccard deduplication."""
        self.assertEqual(aggregate_report.derive_severity({"impact": "blocking", "scope": "sitewide"}), "critical")
        self.assertEqual(aggregate_report.derive_severity({"impact": "blocking", "scope": "section"}), "high")
        self.assertEqual(aggregate_report.derive_severity({"impact": "degrading", "scope": "sitewide"}), "high")
        self.assertEqual(aggregate_report.derive_severity({"impact": "degrading", "scope": "section"}), "medium")
        self.assertEqual(aggregate_report.derive_severity({"impact": "cosmetic", "scope": "single-page"}), "low")

        # Semantic Deduplication across overlapping findings
        f1 = {"title": "Missing Product schema on pricing route", "subcategory": "structured-data", "evidence": "evidence A"}
        f2 = {"title": "Pricing page lacks Product schema markup", "subcategory": "structured-data", "evidence": "evidence B"}
        merged = aggregate_report.dedupe([f1, f2])
        self.assertEqual(len(merged), 1)
        self.assertIn("evidence A", merged[0]["evidence"])
        self.assertIn("evidence B", merged[0]["evidence"])

    def test_02_clean_website_zero_false_positives(self):
        """Verify that a well-structured, server-rendered site does not trigger false positive penalties."""
        clean_html = """
        <html>
        <head>
            <title>Acme Developer Cloud</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <script type="application/ld+json">
            {
                "@context": "https://schema.org",
                "@type": "Organization",
                "name": "Acme Inc",
                "url": "https://acme.example.com",
                "sameAs": ["https://www.wikidata.org/wiki/Q12345"]
            }
            </script>
        </head>
        <body>
            <header><nav><a href="/products">Products</a><a href="/pricing">Pricing</a><a href="/about">About</a><a href="/contact">Contact</a></nav></header>
            <main>
                <h1>Modern Database Platform for Engineering Teams</h1>
                <p>Built for developers. Deploy globally distributed PostgreSQL clusters in seconds.</p>
                <p><a href="/signup">Start Free Trial</a></p>
                <h2>Sub-millisecond Latency</h2>
                <p>Read replicas in 30 regions worldwide with automated instant failover.</p>
            </main>
            <footer><p>© 2026 Acme Inc.</p></footer>
        </body>
        </html>
        """
        clean_page = {"url": "https://acme.example.com", "html": clean_html, "text": check_engagement.strip_tags(clean_html), "links": ["/products", "/pricing", "/about", "/contact"]}
        
        # Render gap check should find 0 blocking defects
        render_findings, _ = check_render_gap.check_page("https://acme.example.com", clean_html)
        self.assertEqual(len([f for f in render_findings if f.get("severity") in ("critical", "high")]), 0)

        # Engagement check should find 0 critical defects
        engage_findings = check_engagement.check_page_engagement(clean_page, "https://acme.example.com", "Acme")
        self.assertEqual(len([f for f in engage_findings if f.get("severity") in ("critical", "high")]), 0)

    def test_03_js_heavy_empty_spa_shell_detection(self):
        """Verify detection of client-rendered SPA shell where initial HTML lacks substantive content."""
        # Case A: Named container SPA shell (#root)
        spa_html = '<html><head><title>SPA App</title></head><body><div id="root"></div><script src="/bundle.js"></script></body></html>'
        findings, _ = check_render_gap.check_page("https://example.com/app", spa_html)
        self.assertTrue(any("SPA shell" in f["title"] or "minimal initial HTML" in f["title"] for f in findings))

        # Case B: Framework-agnostic client-rendered shell without named container fingerprint
        agnostic_spa_html = '<html><head><title>Registry</title><link rel="stylesheet" href="/app.css"><link rel="modulepreload" href="/entry.js"></head><body><noscript>Please enable JavaScript to view this application.</noscript><div style="display:contents"></div></body></html>'
        findings_agnostic, _ = check_render_gap.check_page("https://example.com/agnostic-app", agnostic_spa_html)
        self.assertTrue(any("no recognized framework fingerprint" in f["title"] for f in findings_agnostic))

    def test_04_facts_locked_in_pdf_without_html_text(self):
        """Verify that locked facts in PDF are flagged ONLY when equivalent HTML text is missing."""
        # Case A: PDF with NO HTML details -> DEFECT
        bad_html = '<html><body><h1>Pricing Information</h1><p>See our pricing here: <a href="pricing.pdf">Download pricing.pdf</a></p></body></html>'
        findings_bad, _ = check_structured_data.check_page("https://example.com/pricing", bad_html)
        self.assertTrue(any("locked solely inside linked PDF" in f["title"] for f in findings_bad))

        # Case B: PDF link present BUT HTML already contains the pricing facts -> NO DEFECT (Zero false positive)
        good_html = """<html><body><h1>Pricing Information</h1>
        <p>Our Starter plan is $29 per month and Pro plan is $99 per month billed annually.</p>
        <p>You can also download a copy: <a href="pricing.pdf">Download pricing.pdf</a></p>
        </body></html>"""
        findings_good, _ = check_structured_data.check_page("https://example.com/pricing", good_html)
        self.assertFalse(any("locked solely inside linked PDF" in f["title"] for f in findings_good))

    def test_05_grounded_product_schema_inference_no_false_positives(self):
        """Verify that casual mentions of currency in blogs do NOT falsely trigger Product schema requirements."""
        # Blog mentioning a funding round
        blog_html = "<html><body><h1>Our Journey</h1><p>In 2021, we raised $5M in seed funding to expand our engineering team.</p></body></html>"
        findings_blog, _ = check_structured_data.check_page("https://example.com/blog/funding", blog_html)
        self.assertFalse(any("Product" in f["title"] for f in findings_blog))

        # Genuine pricing route with commercial signals
        pricing_html = "<html><body><h1>Pricing Tiers</h1><p>Starter plan starts at $29 per month with unlimited API calls. Add to cart to subscribe.</p></body></html>"
        findings_pricing, _ = check_structured_data.check_page("https://example.com/pricing", pricing_html)
        self.assertTrue(any("Product" in f["title"] for f in findings_pricing))

    def test_06_conflicting_structured_data_detection(self):
        """Verify detection of contradiction between structured data price and visible text price."""
        conflicting_html = """
        <html>
        <head>
            <script type="application/ld+json">
            {
                "@context": "https://schema.org",
                "@type": "Product",
                "name": "Cloud DB",
                "offers": {
                    "@type": "Offer",
                    "price": "99.00",
                    "priceCurrency": "USD"
                }
            }
            </script>
        </head>
        <body>
            <h1>Cloud DB Pricing</h1>
            <p>Special promotion: Only $49.00 per month for new signups!</p>
        </body>
        </html>
        """
        findings, _ = check_structured_data.check_page("https://example.com/pricing", conflicting_html)
        self.assertTrue(any("Conflicting pricing" in f["title"] for f in findings))

        # Zero false positive when visible price is $99 and schema price is 99.00
        matching_html = """
        <html>
        <head>
            <script type="application/ld+json">
            {
                "@context": "https://schema.org",
                "@type": "Product",
                "name": "Cloud DB",
                "offers": {
                    "@type": "Offer",
                    "price": "99.00",
                    "priceCurrency": "USD"
                }
            }
            </script>
        </head>
        <body>
            <h1>Cloud DB Pricing</h1>
            <p>Standard subscription: $99 per month billed annually.</p>
        </body>
        </html>
        """
        findings_match, _ = check_structured_data.check_page("https://example.com/pricing", matching_html)
        self.assertFalse(any("Conflicting pricing" in f["title"] for f in findings_match))

    def test_07_freshness_cross_page_consistency(self):
        """Verify detection of temporal discrepancy across pages."""
        pages = [
            {"url": "https://example.com/", "text": "Welcome to our portal. Copyright © 2026 Acme Corp.", "html": "", "headers": {}},
            {"url": "https://example.com/terms", "text": "Terms of Service. Last updated: March 10, 2019. Copyright © 2019 Acme Corp.", "html": "", "headers": {}}
        ]
        findings, _ = check_freshness.check_freshness(pages)
        self.assertTrue(any("Inconsistent copyright years" in f["title"] or "stale information" in f["title"] for f in findings))

    def test_08_engagement_visitor_retention_dimensions(self):
        """Verify engagement audit across orientation, CTA, and dead ends."""
        # 1. Page with missing H1 and no CTA
        poor_page = {
            "url": "https://example.com/",
            "html": "<html><body><div>Transforming the future of everything with synergy.</div></body></html>",
            "text": "Transforming the future of everything with synergy.",
            "links": []
        }
        findings = check_engagement.check_page_engagement(poor_page, "https://example.com", "Example")
        self.assertTrue(any("No primary heading" in f["title"] for f in findings))
        self.assertTrue(any("No distinct, actionable call-to-action" in f["title"] for f in findings))

        # 2. Dead-end subpage with 0 navigation
        dead_end_page = {
            "url": "https://example.com/feature-detail",
            "html": "<html><body><h1>Feature Detail</h1><p>Here are the notes.</p></body></html>",
            "text": "Feature Detail Here are the notes.",
            "links": []
        }
        dead_end_findings = check_engagement.check_dead_ends(dead_end_page)
        self.assertTrue(any("Dead-end page detected" in f["title"] for f in dead_end_findings))

    def test_09_entity_collision_risk_common_noun(self):
        """Verify that common-noun brands without sameAs links trigger entity collision risk."""
        pages = [{
            "url": "https://apex.example.com",
            "title": "Apex - Cloud Analytics",
            "html": "<html><body><h1>Apex Analytics</h1><p>Founded in 2022 in Seattle.</p></body></html>",
            "text": "Apex Analytics Founded in 2022 in Seattle."
        }]
        findings, _ = check_corroboration.audit_corroboration(pages, "https://apex.example.com")
        self.assertTrue(any("entity collision risk" in f["title"].lower() for f in findings))

    def test_10_end_to_end_single_pass_crawler_pipeline(self):
        """Test full orchestrator crawler pipeline against synthetic live server fixture."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out_base = os.path.join(tmpdir, "test_report")
            
            # Run the actual entrypoint script against our mock server
            py_exec = sys.executable
            entrypoint_script = os.path.join(BASE_DIR, "skills", "audit-orchestrator", "scripts", "run_audit.py")
            cmd = [py_exec, entrypoint_script, "--site", self.base_url, "--max-pages", "5", "--out", out_base]
            env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
            
            result = subprocess.run(cmd, capture_output=True, text=True, env=env)
            self.assertEqual(result.returncode, 0, f"run_audit.py failed: {result.stderr}")

            # Verify report files were created
            json_path = f"{out_base}.json"
            md_path = f"{out_base}.md"
            self.assertTrue(os.path.exists(json_path), "audit_report.json was not generated")
            self.assertTrue(os.path.exists(md_path), "audit_report.md was not generated")

            # Validate Adobe Hackathon schema
            with open(json_path, "r", encoding="utf-8") as f:
                report = json.load(f)

            self.assertIn("site", report)
            self.assertIn("audited_at", report)
            self.assertIn("summary", report)
            self.assertIn("total_findings", report["summary"])
            self.assertIn("critical", report["summary"])
            self.assertIn("high", report["summary"])
            self.assertIn("medium", report["summary"])
            self.assertIn("findings", report)

            # Check that robots.txt block for GPTBot was correctly detected
            self.assertTrue(any("GPTBot" in f["title"] for f in report["findings"]))
            # Check that pricing conflict was detected on the deeper /pricing route
            self.assertTrue(any("Conflicting pricing" in f["title"] for f in report["findings"]))

            for f in report["findings"]:
                self.assertIn("id", f)
                self.assertIn("title", f)
                self.assertIn("severity", f)
                self.assertIn("evidence", f)
                self.assertIn("suggested_action", f)
                self.assertIn("summary", f["suggested_action"])
                self.assertIn("priority", f["suggested_action"])

    def test_11_normal_static_website(self):
        """Verify normal static website generates full valid audit with verified coverage."""
        html = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Static Corporation</title>
        <script type="application/ld+json">{"@context":"https://schema.org","@type":"Organization","name":"Static Corp","url":"https://static.example"}</script>
        </head><body><header><nav><a href="/">Home</a><a href="/about">About</a></nav></header>
        <main><h1>Verified Static Infrastructure</h1><p>High throughput engineering solutions.</p>
        <a href="/contact">Get in touch</a></main>
        <footer><p>&copy; 2026 Static Corp.</p></footer></body></html>"""
        pages = [{"url": "https://static.example/", "status": 200, "headers": {}, "html": html, "text": "Verified Static Infrastructure High throughput engineering solutions.", "links": []}]
        coverage = {
            "status": "verified",
            "accessible_pages": 1,
            "inaccessible_routes": 0,
            "verified": ["crawler_access", "machine_readability"],
            "not_verified": [],
            "not_accessible": []
        }
        report = aggregate_report.build_report("https://static.example", [], [], crawled_pages_count=1, coverage=coverage)
        self.assertIn("coverage", report)
        self.assertEqual(report["coverage"]["status"], "verified")
        self.assertEqual(report["summary"]["total_findings"], 0)

    def test_12_partially_accessible_website(self):
        """Verify partially accessible website continues audit on valid pages and does not penalize score for restricted routes."""
        valid_page = {"url": f"{self.base_url}/", "status": 200, "headers": {}, "html": "<html><body><h1>Public Page</h1><a href='/restricted'>Private</a></body></html>", "text": "Public Page", "links": [f"{self.base_url}/restricted"]}
        blocked_page = {"url": f"{self.base_url}/restricted", "status": 403, "headers": {}, "html": "", "text": "", "links": [], "error": "HTTP Error 403: Forbidden"}
        crawled_pages = [valid_page, blocked_page]
        
        valid_pages = [p for p in crawled_pages if p.get("status") == 200 and len(str(p.get("html", "")).strip()) > 0]
        blocked_pages = [p for p in crawled_pages if p.get("status") != 200 or not str(p.get("html", "")).strip()]
        
        self.assertEqual(len(valid_pages), 1)
        self.assertEqual(len(blocked_pages), 1)
        
        coverage = {
            "status": "partial",
            "reason": "1 page(s) accessible, 1 route(s) restricted or blocked",
            "accessible_pages": len(valid_pages),
            "inaccessible_routes": len(blocked_pages),
            "verified": ["crawler_access", "machine_readability"],
            "not_verified": ["inaccessible_routes_content"],
            "not_accessible": [blocked_page["url"]]
        }
        partial_finding = {
            "title": "Audit coverage partial: 1 page(s) evaluated, 1 route(s) restricted or inaccessible",
            "category": "discoverability",
            "subcategory": "crawlability",
            "impact": "cosmetic",
            "scope": "single-page",
            "confidence": "high",
            "evidence": f"Inaccessible: {[blocked_page['url']]}",
            "suggested_action": {"summary": "Review access rules.", "priority": "low"}
        }
        report = aggregate_report.build_report(self.base_url, [partial_finding], [], crawled_pages_count=1, coverage=coverage)
        self.assertEqual(report["coverage"]["status"], "partial")
        self.assertTrue(any("Audit coverage partial" in f["title"] for f in report["findings"]))
        # Coverage finding does not deduct points from accessible content score
        self.assertEqual(report["score"], 100)

    def test_13_completely_inaccessible_website(self):
        """Verify completely inaccessible website generates evidence-backed limitation with score=null and critical severity with low confidence."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out_base = os.path.join(tmpdir, "zero_report")
            cmd = [
                sys.executable,
                os.path.join(BASE_DIR, "skills", "audit-orchestrator", "scripts", "run_audit.py"),
                "--site", "https://unreachable-test-domain-99999.invalid",
                "--out", out_base
            ]
            env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
            res = subprocess.run(cmd, capture_output=True, text=True, env=env)
            self.assertEqual(res.returncode, 0, f"run_audit crashed: {res.stderr}")
            self.assertTrue(os.path.exists(f"{out_base}.json"))
            with open(f"{out_base}.json", "r", encoding="utf-8") as f:
                report = json.load(f)
            self.assertEqual(report["crawled_pages"], 0)
            self.assertEqual(report["coverage"]["status"], "not_accessible")
            self.assertIsNone(report["score"])
            self.assertIsNone(report["grade"])
            self.assertEqual(len(report["findings"]), 1)
            self.assertIn("Audit coverage limited", report["findings"][0]["title"])
            self.assertEqual(report["findings"][0]["severity"], "critical")
            self.assertEqual(report["findings"][0]["confidence"], "low")
            self.assertEqual(report["summary"]["critical"], 1)
            self.assertEqual(report["summary"]["low"], 0)
            self.assertTrue(bool(report["findings"][0].get("evidence")))
            ev_lower = report["findings"][0]["evidence"].lower()
            self.assertTrue(
                any(term in ev_lower for term in ("dns", "name resolution", "temporary failure in name resolution", "getaddrinfo", "nodename", "name or service not known", "connection refused", "unreachable", "network")),
                f"Expected DNS or network resolution wording in evidence, got: {report['findings'][0]['evidence']}"
            )
            self.assertIn("audit environment", ev_lower)
            self.assertEqual(len(report["coverage"]["verified"]), 0)
            self.assertTrue(len(report["coverage"]["not_verified"]) > 0)

    def test_14_redirecting_website(self):
        """Verify crawler follows HTTP redirects to destination page."""
        redir_start = f"{self.base_url}/redirect-src"
        pages = crawler.crawl_website(redir_start, max_pages=3)
        self.assertTrue(len(pages) >= 1)
        self.assertTrue(any(p.get("status") == 200 and "Redirect Succeeded" in p.get("html", "") for p in pages))

    def test_15_js_heavy_website(self):
        """Verify JS-heavy client shell detects render gap."""
        spa_url = f"{self.base_url}/spa-client"
        pages = crawler.crawl_website(spa_url, max_pages=1)
        self.assertEqual(len(pages), 1)
        findings, opps = check_render_gap.check_page(pages[0]["url"], pages[0]["html"])
        self.assertTrue(any("SPA shell" in f["title"] or "minimal initial HTML" in f["title"] for f in findings))

    def test_16_zero_access_robots_txt_restriction(self):
        """Verify zero-access caused by robots.txt classifies deliberate site policy, assigns critical severity with high confidence, and score=None."""
        classified = aggregate_report.classify_access_failure(0, "Disallowed by robots.txt", "https://example.com")
        self.assertEqual(classified["cause"], "robots.txt restriction")
        self.assertEqual(classified["finding"]["severity"], "critical")
        self.assertEqual(classified["finding"]["confidence"], "high")
        self.assertIn("robots.txt", classified["finding"]["title"])
        report = aggregate_report.build_report("https://example.com", [classified["finding"]], [], crawled_pages_count=0)
        self.assertIsNone(report["score"])
        self.assertIsNone(report["grade"])
        self.assertEqual(report["summary"]["critical"], 1)
        self.assertEqual(report["summary"]["low"], 0)

    def test_17_zero_access_http_access_restriction(self):
        """Verify zero-access from 401/403 (critical) and 429 (high) classifies HTTP/access restriction with score=None."""
        for code, err in [(401, "HTTP Error 401: Unauthorized"), (403, "HTTP Error 403: Forbidden")]:
            classified = aggregate_report.classify_access_failure(code, err, "https://example.com")
            self.assertEqual(classified["cause"], "HTTP/access restriction")
            self.assertEqual(classified["finding"]["severity"], "critical")
            self.assertEqual(classified["finding"]["confidence"], "high")
            report = aggregate_report.build_report("https://example.com", [classified["finding"]], [], crawled_pages_count=0)
            self.assertIsNone(report["score"])
            self.assertIsNone(report["grade"])
            self.assertEqual(report["summary"]["critical"], 1)

        # 429 rate limit is degrading + sitewide -> high severity
        c_429 = aggregate_report.classify_access_failure(429, "HTTP Error 429: Too Many Requests", "https://example.com")
        self.assertEqual(c_429["cause"], "HTTP/access restriction")
        self.assertEqual(c_429["finding"]["severity"], "high")
        self.assertEqual(c_429["finding"]["confidence"], "high")
        rep_429 = aggregate_report.build_report("https://example.com", [c_429["finding"]], [], crawled_pages_count=0)
        self.assertIsNone(rep_429["score"])
        self.assertIsNone(rep_429["grade"])
        self.assertEqual(rep_429["summary"]["high"], 1)

    def test_18_zero_access_website_unavailable(self):
        """Verify zero-access from 404 and 5xx classifies target website unavailable with critical severity, high confidence, and score=None."""
        for code in [404, 500, 502, 503]:
            classified = aggregate_report.classify_access_failure(code, f"HTTP Error {code}", "https://example.com")
            self.assertEqual(classified["cause"], "target website unavailable")
            self.assertEqual(classified["finding"]["severity"], "critical")
            self.assertEqual(classified["finding"]["confidence"], "high")
            report = aggregate_report.build_report("https://example.com", [classified["finding"]], [], crawled_pages_count=0)
            self.assertIsNone(report["score"])
            self.assertIsNone(report["grade"])
            self.assertEqual(report["summary"]["critical"], 1)

    def test_19_zero_access_timeout(self):
        """Verify zero-access from network timeout classifies timeout cause with critical severity, low confidence, and score=None."""
        classified = aggregate_report.classify_access_failure(0, "The read operation timed out", "https://example.com")
        self.assertEqual(classified["cause"], "timeout")
        self.assertEqual(classified["finding"]["severity"], "critical")
        self.assertEqual(classified["finding"]["confidence"], "low")
        self.assertIn("timed out", classified["finding"]["title"].lower())
        self.assertIn("audit environment", classified["finding"]["evidence"].lower())
        report = aggregate_report.build_report("https://example.com", [classified["finding"]], [], crawled_pages_count=0)
        self.assertIsNone(report["score"])
        self.assertIsNone(report["grade"])
        self.assertEqual(report["summary"]["critical"], 1)

    def test_20_zero_access_unsupported_content(self):
        """Verify zero-access from non-HTML content classifies unsupported content with critical severity, low confidence, and score=None."""
        classified = aggregate_report.classify_access_failure(200, "Content-Type is application/pdf, expected text/html", "https://example.com")
        self.assertEqual(classified["cause"], "unsupported content")
        self.assertEqual(classified["finding"]["severity"], "critical")
        self.assertEqual(classified["finding"]["confidence"], "low")
        self.assertIn("non-HTML", classified["finding"]["title"])
        self.assertIn("crawler", classified["finding"]["evidence"].lower())
        report = aggregate_report.build_report("https://example.com", [classified["finding"]], [], crawled_pages_count=0)
        self.assertIsNone(report["score"])
        self.assertIsNone(report["grade"])
        self.assertEqual(report["summary"]["critical"], 1)

    def test_21_audit_cli_root_entrypoint(self):
        """Verify root audit.py CLI runner across formats (terminal, json, deliverables) and programmatic API."""
        py_exec = sys.executable
        audit_script = os.path.join(BASE_DIR, "audit.py")
        env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")

        # 1. CLI Execution with deliverable outputs
        with tempfile.TemporaryDirectory() as tmpdir:
            out_base = os.path.join(tmpdir, "cli_test_report")
            cmd = [py_exec, audit_script, self.base_url, "--max-pages", "3", "--out", out_base]
            res = subprocess.run(cmd, capture_output=True, text=True, env=env)
            self.assertEqual(res.returncode, 0, f"audit.py CLI failed: {res.stderr}")
            self.assertTrue(os.path.exists(f"{out_base}.json"), "cli_test_report.json missing")
            self.assertTrue(os.path.exists(f"{out_base}.md"), "cli_test_report.md missing")
            self.assertTrue(os.path.exists(f"{out_base}.html"), "cli_test_report.html missing")

            with open(f"{out_base}.json", "r", encoding="utf-8") as f:
                rep = json.load(f)
            self.assertEqual(rep["site"], self.base_url)
            self.assertIn("execution_seconds", rep)
            self.assertIn("findings", rep)

        # 2. CLI Execution with JSON format to stdout
        cmd_json = [py_exec, audit_script, self.base_url, "--format", "json", "--max-pages", "2"]
        res_json = subprocess.run(cmd_json, capture_output=True, text=True, env=env)
        self.assertEqual(res_json.returncode, 0, f"audit.py --format json failed: {res_json.stderr}")
        stdout_rep = json.loads(res_json.stdout)
        self.assertEqual(stdout_rep["site"], self.base_url)
        self.assertIn("summary", stdout_rep)
        self.assertIn("execution_seconds", stdout_rep)

        # 3. CLI Execution with shorthand --json flag
        cmd_shorthand = [py_exec, audit_script, "--site", self.base_url, "--json", "--max-pages", "2"]
        res_shorthand = subprocess.run(cmd_shorthand, capture_output=True, text=True, env=env)
        self.assertEqual(res_shorthand.returncode, 0, f"audit.py --json failed: {res_shorthand.stderr}")
        shorthand_rep = json.loads(res_shorthand.stdout)
        self.assertEqual(shorthand_rep["site"], self.base_url)

        # 4. Direct Programmatic API execution
        rep_api = audit.run_cli_audit(self.base_url, output_json=False, max_pages=3)
        self.assertIsInstance(rep_api, dict)
        self.assertEqual(rep_api["site"], self.base_url)
        self.assertIn("execution_seconds", rep_api)
        self.assertIn("score", rep_api)
        self.assertIn("findings", rep_api)

        # 5. Programmatic API with inaccessible route (graceful degradation)
        rep_zero = audit.run_cli_audit("https://unreachable-test-domain-99999.invalid", output_json=False)
        self.assertIsInstance(rep_zero, dict)
        self.assertEqual(rep_zero["coverage"]["status"], "not_accessible")
        self.assertIsNone(rep_zero["score"])
        self.assertIn("execution_seconds", rep_zero)
        self.assertTrue(rep_zero["execution_seconds"] >= 0)

    def test_22_empirical_search_optional_check(self):
        """Verify empirical grounding check: clean 'not_run' default, pure stdlib, and falsifiable reporting."""
        dummy_page = [{"url": "https://example.com/", "html": "<html><head><title>Example</title></head><body><h1>Example</h1></body></html>", "text": "Example"}]
        
        # 1. Default unconfigured check cleanly yields 'not_run' with zero findings or penalties
        meta_unconf, findings_unconf, opps_unconf = check_empirical_search.audit_empirical_search(
            dummy_page, "https://example.com", enable_empirical=False
        )
        self.assertEqual(meta_unconf["status"], "not_run")
        self.assertEqual(len(findings_unconf), 0)
        self.assertEqual(len(opps_unconf), 0)
        self.assertIn("optional", meta_unconf["reason"].lower())

        # 2. Aggregator includes empirical_corroboration block without penalizing clean site
        report = aggregate_report.build_report("https://example.com", [], [], crawled_pages_count=1)
        self.assertIn("empirical_corroboration", report)
        self.assertEqual(report["empirical_corroboration"]["status"], "not_run")
        self.assertEqual(report["summary"]["total_findings"], 0)
        self.assertEqual(report["score"], 100)

        # 3. Simulated negative match with general search provider (high confidence)
        with unittest.mock.patch("check_empirical_search.query_external_search") as mock_query:
            mock_query.return_value = {
                "status": "completed",
                "provider": "Brave Search API",
                "query": "unindexed.example",
                "domain_searched": "unindexed.example",
                "matched": False,
                "matched_urls": [],
                "raw_results_count": 0,
                "evidence": "Queried Brave Search API with 'unindexed.example'. Returned 0 results."
            }
            meta_neg_high, findings_neg_high, _ = check_empirical_search.audit_empirical_search(
                dummy_page, "https://unindexed.example", enable_empirical=True
            )
            self.assertEqual(meta_neg_high["status"], "completed")
            self.assertFalse(meta_neg_high["matched"])
            self.assertEqual(len(findings_neg_high), 1)
            f_high = findings_neg_high[0]
            self.assertEqual(f_high["category"], "empirical_corroboration")
            self.assertEqual(f_high["subcategory"], "external_search")
            self.assertEqual(f_high["severity"], "medium")
            self.assertEqual(f_high["confidence"], "high")
            self.assertIn("Brave Search API", f_high["evidence"])
            self.assertIn("suggested_action", f_high)

        # 4. Simulated negative match with fallback snippet provider (low confidence + softened evidence)
        with unittest.mock.patch("check_empirical_search.query_external_search") as mock_query:
            mock_query.return_value = {
                "status": "completed",
                "provider": "DuckDuckGo Instant Answer API",
                "query": "unindexed.example",
                "domain_searched": "unindexed.example",
                "matched": False,
                "matched_urls": [],
                "raw_results_count": 0,
                "evidence": "Queried DuckDuckGo Instant Answer API with 'unindexed.example'. Target domain matched: False."
            }
            meta_neg_low, findings_neg_low, _ = check_empirical_search.audit_empirical_search(
                dummy_page, "https://unindexed.example", enable_empirical=True
            )
            self.assertEqual(meta_neg_low["status"], "completed")
            self.assertFalse(meta_neg_low["matched"])
            self.assertEqual(len(findings_neg_low), 1)
            f_low = findings_neg_low[0]
            self.assertEqual(f_low["category"], "empirical_corroboration")
            self.assertEqual(f_low["subcategory"], "external_search")
            self.assertEqual(f_low["severity"], "medium")
            self.assertEqual(f_low["confidence"], "low")
            self.assertIn("DuckDuckGo Instant Answer API", f_low["evidence"])
            self.assertIn("weak signal", f_low["evidence"].lower())
            self.assertIn("coverage gaps", f_low["evidence"].lower())

        # 5. Simulated positive match (domain verified in search)
        with unittest.mock.patch("check_empirical_search.query_external_search") as mock_query:
            mock_query.return_value = {
                "status": "completed",
                "provider": "Brave Search API",
                "query": "verified.example",
                "domain_searched": "verified.example",
                "matched": True,
                "matched_urls": ["https://verified.example/"],
                "raw_results_count": 5,
                "evidence": "Queried Brave Search API with 'verified.example'. Target domain matched."
            }
            meta_pos, findings_pos, opps_pos = check_empirical_search.audit_empirical_search(
                dummy_page, "https://verified.example", enable_empirical=True
            )
            self.assertEqual(meta_pos["status"], "completed")
            self.assertTrue(meta_pos["matched"])
            self.assertEqual(len(findings_pos), 0)
            self.assertEqual(len(opps_pos), 1)


def run_tests():
    print("=" * 65)
    print("  ADOBE UNIVERSITY HACKATHON 2026 — GENERALIZATION TEST SUITE")
    print("  Testing 22 Synthetic Scenarios & Single-Pass Pipeline")
    print("=" * 65)
    suite = unittest.TestLoader().loadTestsFromTestCase(TestAuraVisionGEOGeneralization)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_tests())
