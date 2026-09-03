#!/usr/bin/env python3
"""
Static, read-only crawlability checks. Stdlib-only (urllib) — no third-party
dependencies, so this runs anywhere Python 3.8+ runs.

Usage:
    python check_crawlability.py --site https://example.com \
        --pages https://example.com/pricing https://example.com/products \
        --out crawl_findings.json
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

USER_AGENT = "Aura-Vision-GEO/1.0 (+read-only site audit; respects robots.txt)"
TIMEOUT = 4

# Known AI-agent / answer-engine fetcher tokens worth checking explicitly.
# '*' (the default group) is always checked too.
AI_AGENTS = [
    "GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "anthropic-ai",
    "Claude-Web", "PerplexityBot", "Google-Extended", "CCBot", "Bytespider",
    "Amazonbot", "Applebot-Extended",
]

STALE_SITEMAP_DAYS = 365


def fetch_raw(url, headers=None):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.status, dict(resp.getheaders()), resp.read()


def fetch(url, headers=None):
    status, headers_dict, raw_bytes = fetch_raw(url, headers)
    # Handle transparent gzip decompression if server sent compressed bytes
    if raw_bytes.startswith(b"\x1f\x8b") or url.endswith(".gz"):
        try:
            raw_bytes = gzip.decompress(raw_bytes)
        except Exception:
            pass
    return status, headers_dict, raw_bytes.decode("utf-8", errors="replace")


def check_robots(site_root, sample_paths):
    findings, opportunities = [], []
    robots_url = urljoin(site_root, "/robots.txt")
    try:
        status, _, body = fetch(robots_url)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
        # No robots.txt at all is not a violation — default is "everything allowed" —
        # but it *is* a missed opportunity to point crawlers at the sitemap.
        opportunities.append({
            "title": "No robots.txt found",
            "suggested_action": {
                "summary": "Publish a robots.txt with an explicit Sitemap: line, "
                            "even if it allows everything — it's the first place "
                            "crawlers look for a fast path to your content.",
                "priority": "low",
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
        findings.append({
            "title": f"robots.txt blocks known AI/answer-engine crawlers: {', '.join(blocked_agents)}",
            "category": "discoverability",
            "subcategory": "crawlability",
            "impact": "blocking",
            "scope": "sitewide" if sitewide else "section",
            "confidence": "high",
            "evidence": f"can_fetch() returned False for {blocked_agents} against {site_root} "
                        f"per {robots_url}",
            "suggested_action": {
                "summary": "Remove or narrow the Disallow rules for these agents unless the "
                            "block is intentional (e.g. paywalled/private content).",
                "priority": "critical" if sitewide else "high",
                "mechanism": "A blocked crawler can't fetch the page at all — this isn't a "
                              "ranking penalty, the content is architecturally invisible to "
                              "that system regardless of quality.",
            },
        })

    # Sample specific paths too — a site can allow '/' but disallow the exact
    # section being audited.
    path_blocked = [p for p in sample_paths if not rfp.can_fetch("*", p)]
    if path_blocked and not blocked_agents:
        findings.append({
            "title": f"robots.txt disallows {len(path_blocked)} audited path(s)",
            "category": "discoverability",
            "subcategory": "crawlability",
            "impact": "blocking",
            "scope": "section",
            "confidence": "high",
            "evidence": f"Disallowed paths: {path_blocked}",
            "suggested_action": {
                "summary": "Confirm these disallows are intentional; if not, narrow them.",
                "priority": "high",
            },
        })

    sitemap_urls = list(rfp.site_maps() or [])
    if not sitemap_urls:
        opportunities.append({
            "title": "robots.txt doesn't reference a sitemap",
            "suggested_action": {
                "summary": "Add 'Sitemap: https://.../sitemap.xml' to robots.txt.",
                "priority": "low",
            },
        })
    else:
        sm_findings, sm_opps = check_sitemap_freshness(sitemap_urls[0])
        findings.extend(sm_findings)
        opportunities.extend(sm_opps)

    # Check for llms.txt opportunity
    llms_url = urljoin(site_root, "/llms.txt")
    try:
        l_status, _, l_body = fetch(llms_url)
        if l_status != 200 or len(l_body.strip()) < 10 or "<html" in l_body.lower():
            opportunities.append({
                "title": "Publish an llms.txt at the site root",
                "suggested_action": {
                    "summary": "Add /llms.txt pointing AI agents at your canonical markdown entry point.",
                    "priority": "low",
                },
            })
    except Exception:
        opportunities.append({
            "title": "Publish an llms.txt at the site root",
            "suggested_action": {
                "summary": "Add /llms.txt pointing AI agents at your canonical markdown entry point.",
                "priority": "low",
            },
        })

    return findings, opportunities


def check_sitemap_freshness(sitemap_url):
    findings, opportunities = [], []
    try:
        _, _, body = fetch(sitemap_url)
        root = ET.fromstring(body)
    except Exception as e:
        findings.append({
            "title": "Sitemap is referenced but not fetchable/parseable",
            "category": "discoverability",
            "subcategory": "crawlability",
            "impact": "degrading",
            "scope": "sitewide",
            "confidence": "high",
            "evidence": f"GET {sitemap_url} failed or returned invalid XML: {e}",
            "suggested_action": {"summary": "Fix or regenerate the sitemap.", "priority": "medium"},
        })
        return findings, opportunities

    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    lastmods = [el.text for el in root.findall(".//sm:lastmod", ns) if el.text]
    if not lastmods:
        opportunities.append({
            "title": "Sitemap has no <lastmod> dates",
            "suggested_action": {
                "summary": "Add <lastmod> to sitemap entries so crawlers can prioritize "
                            "re-fetching changed pages.",
                "priority": "low",
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
                "title": "Sitemap lastmod dates are stale sitewide",
                "category": "discoverability",
                "subcategory": "crawlability",
                "impact": "degrading",
                "scope": "sitewide",
                "confidence": "high",
                "evidence": f"Newest <lastmod> across {len(parsed)} URLs is {newest.date()} "
                            f"({age_days} days old).",
                "suggested_action": {
                    "summary": "Regenerate the sitemap so lastmod reflects real content changes.",
                    "priority": "medium",
                },
            })
    return findings, opportunities


def check_meta_robots(pages):
    """pages: list of (url, status, headers, html)"""
    findings = []
    noindexed = []
    noindex_re = re.compile(
        r'<meta[^>]+name=["\']robots["\'][^>]+content=["\'][^"\']*noindex', re.IGNORECASE
    )
    for url, status, headers, html in pages:
        # Avoid checking 403/500 security challenge pages for application-level noindex
        if status != 200 and status is not None:
            continue
        header_noindex = "noindex" in headers.get("X-Robots-Tag", "").lower()
        meta_noindex = bool(noindex_re.search(html or ""))
        if header_noindex or meta_noindex:
            noindexed.append(url)
    if noindexed:
        findings.append({
            "title": f"{len(noindexed)} public page(s) are marked noindex",
            "category": "discoverability",
            "subcategory": "crawlability",
            "impact": "blocking",
            "scope": "sitewide" if len(noindexed) > 1 else "single-page",
            "confidence": "high",
            "evidence": f"noindex detected on: {noindexed}",
            "suggested_action": {
                "summary": "Remove noindex from pages meant to be publicly discoverable.",
                "priority": "critical" if len(noindexed) > 1 else "high",
            },
        })
    return findings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True)
    ap.add_argument("--pages", nargs="*", default=[])
    ap.add_argument("--out", default="crawl_findings.json")
    args = ap.parse_args()

    parsed = urlparse(args.site)
    site_root = f"{parsed.scheme}://{parsed.netloc}/"

    findings, opportunities = check_robots(site_root, args.pages or [site_root])

    fetched_pages = []
    for url in (args.pages or [site_root]):
        try:
            status, headers, html = fetch(url)
            fetched_pages.append((url, status, headers, html))
        except Exception as e:
            print(f"warning: could not fetch {url}: {e}", file=sys.stderr)

    findings.extend(check_meta_robots(fetched_pages))

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"findings": findings, "opportunities": opportunities}, f, indent=2, ensure_ascii=False)
    print(f"Wrote {args.out}: {len(findings)} findings, {len(opportunities)} opportunities",
          file=sys.stderr)


if __name__ == "__main__":
    main()
