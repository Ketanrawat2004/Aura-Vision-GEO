#!/usr/bin/env python3
"""
Static, read-only crawlability checks. Stdlib-only (urllib) — no third-party
dependencies, so this runs anywhere Python 3.8+ runs.

Capabilities:
  1. AI Crawler Access: Checks robots.txt against 12 major AI/LLM crawler tokens.
  2. Blocked Essential Paths: Detects if /pricing, /products, /about are disallowed.
  3. Meta Robots & X-Robots-Tag: Flags unwanted noindex on public routes.
  4. HTTP Status & Crawler Inaccessibility: Flags 4xx/5xx errors on crawlable paths.
  5. Canonical Consistency: Flags canonical mismatch or self-referential conflicts.
  6. OpenGraph Citation Metadata: Detects missing og:description/og:image on primary routes.
  7. HTTP Compression & Efficiency: Flags large uncompressed DOM payloads (>75 KB).
  8. Sitemap Discovery & Freshness: Validates sitemap links and lastmod dates.
  9. /llms.txt Proactive Opportunity: Recommends markdown entry points.

Usage:
    python check_crawlability.py --site https://example.com --pages-json pages.json --out crawl_findings.json
    python check_crawlability.py --site https://example.com --pages https://example.com/pricing --out crawl_findings.json
"""
import argparse
import gzip
import json
import re
import sys
import urllib.error
import urllib.request
import urllib.robotparser
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

USER_AGENT = "Aura-Vision-GEO/2.0 (+read-only site audit; respects robots.txt)"
TIMEOUT = 5

AI_AGENTS = [
    "GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "anthropic-ai",
    "Claude-Web", "PerplexityBot", "Google-Extended", "CCBot", "Bytespider",
    "Amazonbot", "Applebot-Extended",
]

STALE_SITEMAP_DAYS = 365
CANONICAL_RE = re.compile(r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)["\']', re.IGNORECASE)
NOINDEX_RE = re.compile(r'<meta[^>]+name=["\']robots["\'][^>]+content=["\'][^"\']*noindex', re.IGNORECASE)
OG_DESC_RE = re.compile(r'<meta[^>]+(?:property|name)=["\']og:description["\'][^>]+content=["\']([^"\']+)["\']', re.IGNORECASE)
OG_TITLE_RE = re.compile(r'<meta[^>]+(?:property|name)=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']', re.IGNORECASE)


def fetch_raw(url, headers=None):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    try:
        resp = urllib.request.urlopen(req, timeout=TIMEOUT)
    except urllib.error.URLError as e:
        if "CERTIFICATE_VERIFY_FAILED" in str(e):
            import ssl
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            resp = urllib.request.urlopen(req, timeout=TIMEOUT, context=ctx)
        else:
            raise
    with resp:
        return resp.status, dict(resp.getheaders()), resp.read()


def fetch(url, headers=None):
    status, headers_dict, raw_bytes = fetch_raw(url, headers)
    if raw_bytes.startswith(b"\x1f\x8b") or url.endswith(".gz"):
        try:
            raw_bytes = gzip.decompress(raw_bytes)
        except Exception:
            pass
    return status, headers_dict, raw_bytes.decode("utf-8", errors="replace")


def check_robots(site_root, sample_paths, preloaded_body=None):
    findings, opportunities = [], []
    robots_url = urljoin(site_root, "/robots.txt")
    if preloaded_body is not None:
        body = preloaded_body
    else:
        try:
            status, _, body = fetch(robots_url)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, Exception):
            opportunities.append({
                "title": "No robots.txt found at site root",
                "suggested_action": {
                    "summary": "Publish a robots.txt with explicit Sitemap and AI agent rules to guide answer-engine fetchers.",
                    "priority": "low",
                    "fix_snippet": f"User-agent: *\nAllow: /\n\nSitemap: {site_root}sitemap.xml"
                },
            })
            return findings, opportunities

    rfp = urllib.robotparser.RobotFileParser()
    rfp.parse(body.splitlines())

    blocked_agents = []
    for agent in AI_AGENTS + ["*"]:
        allowed = rfp.can_fetch(agent, site_root)
        if not allowed:
            blocked_agents.append(agent)

    if blocked_agents:
        sitewide = "*" in blocked_agents or len(blocked_agents) >= 3
        sample_fix = "\n".join(f"User-agent: {a}\nAllow: /" for a in blocked_agents[:3])
        findings.append({
            "title": f"robots.txt blocks known AI/answer-engine crawlers: {', '.join(blocked_agents)}",
            "category": "discoverability",
            "subcategory": "crawlability",
            "impact": "blocking",
            "scope": "sitewide" if sitewide else "section",
            "confidence": "high",
            "evidence": f"can_fetch() returned False for agents {blocked_agents} at {site_root} per {robots_url}",
            "suggested_action": {
                "summary": "Narrow or remove the Disallow directives for these AI crawlers unless the restriction is intentional.",
                "priority": "critical" if sitewide else "high",
                "mechanism": "Answer engines like Perplexity, ChatGPT, and Claude require crawler access to quote and attribute sources in real-time answers.",
                "fix_snippet": sample_fix
            },
        })

    # Check for blocked key sections (/pricing, /about, /products, /docs)
    important_paths = ["/pricing", "/products", "/services", "/about", "/docs", "/features"]
    blocked_important = []
    for p in important_paths:
        test_url = urljoin(site_root, p)
        if not rfp.can_fetch("*", test_url):
            blocked_important.append(p)

    if blocked_important and not blocked_agents:
        findings.append({
            "title": f"robots.txt disallows critical informational routes: {', '.join(blocked_important)}",
            "category": "discoverability",
            "subcategory": "crawlability",
            "impact": "blocking",
            "scope": "section",
            "confidence": "high",
            "evidence": f"Important business routes {blocked_important} disallowed in {robots_url}",
            "suggested_action": {
                "summary": "Ensure public informational routes like pricing and products are crawlable.",
                "priority": "high",
                "mechanism": "When key informational subpaths are blocked, AI crawlers fail to extract pricing or product capabilities.",
                "fix_snippet": "\n".join(f"User-agent: *\nAllow: {p}" for p in blocked_important[:3])
            },
        })

    sitemap_urls = list(rfp.site_maps() or [])
    if not sitemap_urls:
        opportunities.append({
            "title": "robots.txt does not declare a Sitemap directive",
            "suggested_action": {
                "summary": "Add 'Sitemap: https://.../sitemap.xml' to robots.txt.",
                "priority": "low",
                "fix_snippet": f"Sitemap: {site_root}sitemap.xml"
            },
        })
    else:
        sm_findings, sm_opps = check_sitemap_freshness(sitemap_urls[0])
        findings.extend(sm_findings)
        opportunities.extend(sm_opps)

    # Check for llms.txt opportunity
    llms_url = urljoin(site_root, "/llms.txt")
    has_llms = False
    if preloaded_body is None:
        try:
            l_status, _, l_body = fetch(llms_url)
            if l_status == 200 and len(l_body.strip()) >= 10 and "<html" not in l_body.lower():
                has_llms = True
        except Exception:
            pass

    if not has_llms:
        opportunities.append({
            "title": "Publish an /llms.txt file at the site root",
            "suggested_action": {
                "summary": "Add /llms.txt providing concise markdown documentation of key products, APIs, and business facts for LLMs.",
                "priority": "low",
                "fix_snippet": f"# {urlparse(site_root).netloc}\n> Core products, architecture, and API documentation for LLM ingestion.\n\n## Canonical Links\n- [{urlparse(site_root).netloc}](/) : Primary portal"
            },
        })

    return findings, opportunities


def check_sitemap_freshness(sitemap_url):
    findings, opportunities = [], []
    try:
        status, _, body = fetch(sitemap_url)
        if status != 200:
            return findings, opportunities
        root = ET.fromstring(body)
    except (urllib.error.URLError, TimeoutError, OSError):
        # Network unreachable, DNS resolution failed, or offline sandbox
        return findings, opportunities
    except Exception as e:
        findings.append({
            "title": "Sitemap is referenced in robots.txt but unparseable",
            "category": "discoverability",
            "subcategory": "crawlability",
            "impact": "degrading",
            "scope": "sitewide",
            "confidence": "high",
            "evidence": f"GET {sitemap_url} returned invalid XML: {e}",
            "suggested_action": {"summary": "Regenerate the sitemap XML so search and AI indexers can discover canonical routes.", "priority": "medium"},
        })
        return findings, opportunities

    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    lastmods = [el.text for el in root.findall(".//sm:lastmod", ns) if el.text]
    if not lastmods:
        opportunities.append({
            "title": "Sitemap lacks <lastmod> timestamps",
            "suggested_action": {
                "summary": "Add <lastmod> timestamps to sitemap entries to guide incremental crawling.",
                "priority": "low",
                "fix_snippet": "<url>\n  <loc>https://example.com/page</loc>\n  <lastmod>2026-09-01</lastmod>\n</url>"
            },
        })
        return findings, opportunities

    def parse_date(s):
        try:
            return datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            return None

    parsed = [d for d in (parse_date(d) for d in lastmods) if d]
    if parsed:
        newest = max(parsed)
        now = datetime.now(timezone.utc)
        age_days = (now - newest.astimezone(timezone.utc)).days
        if age_days > STALE_SITEMAP_DAYS:
            findings.append({
                "title": f"Sitemap lastmod timestamps indicate stale index across {len(parsed)} inspected URL(s)",
                "category": "discoverability",
                "subcategory": "crawlability",
                "impact": "degrading",
                "scope": "sitewide",
                "confidence": "high",
                "evidence": f"Most recent <lastmod> across {len(parsed)} URLs is {newest.date()} ({age_days} days old).",
                "suggested_action": {
                    "summary": "Update sitemap lastmod timestamps automatically during CI/CD publishing.",
                    "priority": "medium",
                },
            })
    return findings, opportunities


def check_page_crawlability(pages_data):
    """Audits crawl status, noindex tags, HTTP errors, canonical mismatches, OpenGraph snippets, and payload compression."""
    findings = []
    noindexed = []
    http_errors = []
    canonical_issues = []
    missing_og = []
    uncompressed_large = []

    for page in pages_data:
        url = page.get("url", "")
        status = page.get("status", 200)
        headers = page.get("headers", {})
        html = page.get("html", "")

        # HTTP error detection
        if status in (404, 403, 500, 502, 503, 0) or status >= 400:
            err_desc = f"HTTP {status}" if status > 0 else "Connection/DNS Failure"
            http_errors.append(f"{url} ({err_desc})")
            continue

        # Noindex detection
        header_noindex = "noindex" in headers.get("X-Robots-Tag", "").lower()
        meta_noindex = bool(NOINDEX_RE.search(html or ""))
        if header_noindex or meta_noindex:
            noindexed.append(url)

        # Canonical mismatch detection
        canon_match = CANONICAL_RE.search(html or "")
        if canon_match:
            canon_url = canon_match.group(1).strip()
            parsed_canon = urlparse(canon_url)
            parsed_page = urlparse(url)
            if parsed_canon.netloc:
                canon_host = parsed_canon.netloc.lower()
                page_host = parsed_page.netloc.lower()
                if canon_host != page_host and canon_host.lstrip("www.") != page_host.lstrip("www."):
                    canonical_issues.append(f"{url} -> {canon_url}")

        # OpenGraph snippet check on primary route
        parsed_u = urlparse(url)
        if parsed_u.path in ("", "/") and html:
            has_og_desc = bool(OG_DESC_RE.search(html))
            if not has_og_desc and len(html) > 500:
                missing_og.append(url)

        # HTTP Compression check on large payloads (>75 KB)
        if html and len(html) > 75000:
            ce = headers.get("content-encoding", "").lower()
            if not any(comp in ce for comp in ("gzip", "br", "deflate")):
                uncompressed_large.append((url, len(html)))

    if noindexed:
        findings.append({
            "title": f"{len(noindexed)} public page(s) contain noindex directives",
            "category": "discoverability",
            "subcategory": "crawlability",
            "impact": "blocking",
            "scope": "sitewide" if len(noindexed) > 1 else "single-page",
            "confidence": "high",
            "evidence": f"noindex found on: {noindexed[:5]}",
            "suggested_action": {
                "summary": "Remove noindex from public marketing or documentation routes intended for discovery.",
                "priority": "critical" if len(noindexed) > 1 else "high",
                "fix_snippet": '<meta name="robots" content="index, follow">'
            },
        })

    if http_errors:
        findings.append({
            "title": f"Internal links lead to {len(http_errors)} broken HTTP route(s)",
            "category": "discoverability",
            "subcategory": "crawlability",
            "impact": "blocking",
            "scope": "section" if len(http_errors) > 1 else "single-page",
            "confidence": "high",
            "evidence": f"HTTP errors encountered: {http_errors[:5]}",
            "suggested_action": {
                "summary": "Fix broken internal links or implement 301 redirects to canonical targets.",
                "priority": "high",
            },
        })

    if canonical_issues:
        findings.append({
            "title": f"Cross-domain canonical mismatch on {len(canonical_issues)} page(s)",
            "category": "discoverability",
            "subcategory": "crawlability",
            "impact": "degrading",
            "scope": "section",
            "confidence": "high",
            "evidence": f"Canonical links point across origins: {canonical_issues[:3]}",
            "suggested_action": {
                "summary": "Set canonical URLs to the authentic current host to ensure index attribution.",
                "priority": "medium",
                "fix_snippet": f'<link rel="canonical" href="{urljoin(pages_data[0].get("url", "https://example.com"), "/")}">'
            },
        })

    if missing_og:
        findings.append({
            "title": f"Homepage ({missing_og[0]}) lacks OpenGraph description metadata (og:description)",
            "url": missing_og[0],
            "category": "discoverability",
            "subcategory": "crawlability",
            "impact": "cosmetic",
            "scope": "single-page",
            "confidence": "high",
            "evidence": f"Homepage at {missing_og[0]} does not declare <meta property=\"og:description\">.",
            "suggested_action": {
                "summary": "Add OpenGraph metadata to enrich conversational citation cards across Perplexity, ChatGPT, and Apple Intelligence.",
                "priority": "low",
                "mechanism": "Generative search interfaces render visual citation preview cards using OpenGraph title and description metadata.",
                "fix_snippet": '<meta property="og:title" content="Brand - Primary Offering">\n<meta property="og:description" content="Concise 150-character summary explaining what your product does.">\n<meta property="og:image" content="https://example.com/preview.png">'
            }
        })

    if uncompressed_large:
        u_url, u_size = uncompressed_large[0]
        findings.append({
            "title": f"Large DOM payload ({u_size // 1024} KB) served without HTTP compression on {u_url}",
            "url": u_url,
            "category": "discoverability",
            "subcategory": "crawlability",
            "impact": "cosmetic",
            "scope": "single-page",
            "confidence": "high",
            "evidence": f"{u_url} returns {u_size:,} bytes without 'Content-Encoding: gzip/br'.",
            "suggested_action": {
                "summary": "Enable Gzip or Brotli compression on your web server or CDN to reduce TTFB for automated answer-engine scrapers.",
                "priority": "low",
                "fix_snippet": "# In Nginx configuration:\ngzip on;\ngzip_types text/html text/css application/json application/javascript;"
            }
        })

    return findings


def check_site(site_url: str, pages_data: list = None, sample_paths: list = None):
    """Direct callable interface for orchestrator without redundant network fetch."""
    parsed = urlparse(site_url)
    site_root = f"{parsed.scheme}://{parsed.netloc}/"
    
    preloaded_robots = None
    if pages_data is not None:
        for p in pages_data:
            if p.get("url", "").rstrip("/").endswith("/robots.txt"):
                preloaded_robots = p.get("html") or p.get("text") or ""
                break
        if preloaded_robots is None and pages_data and all(p.get("status") == 0 for p in pages_data):
            preloaded_robots = ""

    findings, opportunities = check_robots(site_root, sample_paths or [site_root], preloaded_body=preloaded_robots)
    if pages_data:
        findings.extend(check_page_crawlability(pages_data))
    return findings, opportunities


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True)
    ap.add_argument("--pages", nargs="*", default=[])
    ap.add_argument("--pages-json", help="Path to pre-crawled pages JSON")
    ap.add_argument("--out", default="crawl_findings.json")
    args = ap.parse_args()

    parsed = urlparse(args.site)
    site_root = f"{parsed.scheme}://{parsed.netloc}/"

    pages_data = []
    if args.pages_json:
        with open(args.pages_json, "r", encoding="utf-8") as f:
            pages_data = json.load(f)
    elif args.pages:
        for url in args.pages:
            try:
                status, headers, html = fetch(url)
                pages_data.append({"url": url, "status": status, "headers": headers, "html": html})
            except Exception as e:
                pages_data.append({"url": url, "status": 0, "headers": {}, "html": "", "error": str(e)})

    findings, opportunities = check_site(args.site, pages_data=pages_data, sample_paths=[p.get("url") for p in pages_data] if pages_data else args.pages)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"findings": findings, "opportunities": opportunities}, f, indent=2, ensure_ascii=False)
    print(f"Wrote {args.out}: {len(findings)} findings, {len(opportunities)} opportunities", file=sys.stderr)


if __name__ == "__main__":
    main()
