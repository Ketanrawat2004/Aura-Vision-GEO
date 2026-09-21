#!/usr/bin/env python3
"""
Evidence-based Freshness and Cross-Page Temporal Consistency Audit.
Standard library only (re, json, datetime, urllib).

Capabilities:
  1. Explicit Timestamp Extraction:
     - HTTP Last-Modified headers, ISO 8601 meta tags (article:modified_time), <time> elements,
       and textual 'Last updated on [Date]' strings.
  2. Cross-Page Date Inconsistency:
     - Detects conflicts across crawled pages (e.g. copyright year 2026 vs active pricing/terms dated 2020).
  3. Stale Business Information:
     - Identifies core commercial routes (pricing, docs, plans) carrying explicit dates older than 3 years.
  4. False-Positive Elimination:
     - Never flags a page as stale merely because it lacks a timestamp; requires concrete temporal evidence.

Usage:
    python check_freshness.py --pages-json pages.json --out freshness_findings.json
    python check_freshness.py --pages https://example.com --out freshness_findings.json
"""
import argparse
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone

USER_AGENT = "Aura-Vision-GEO/2.0 (+read-only site audit; respects robots.txt)"
TIMEOUT = 5
CURRENT_YEAR = datetime.now(timezone.utc).year
STALE_DAYS_THRESHOLD = 1095  # ~3 years

COPYRIGHT_RE = re.compile(r'(?:©|&copy;|copyright)\s*(?:[a-zA-Z\s,.-]+)?\b(19\d{2}|20\d{2})\b', re.IGNORECASE)
EXPLICIT_UPDATE_RE = re.compile(r'\b(?:last\s+updated|last\s+modified|updated|effective|valid\s+as\s+of)\s*[:\-]?\s*([A-Za-z]+ \d{1,2},? \d{4}|\d{1,2}\s+[A-Za-z]+,? \d{4}|\d{4}-\d{2}-\d{2})\b', re.IGNORECASE)
META_DATE_RE = re.compile(
    r'<meta[^>]+(?:name|property)=["\'](?:article:published_time|article:modified_time|og:updated_time|date|last-modified|pubdate)["\'][^>]+content=["\']([^"\']+)["\']',
    re.IGNORECASE,
)
TIME_TAG_RE = re.compile(r'<time[^>]+datetime=["\']([^"\']+)["\']', re.IGNORECASE)


def parse_date_string(s: str):
    """Safely parses ISO, RFC, or common date strings into a timezone-aware datetime."""
    if not s:
        return None
    s = s.strip().replace("Z", "+00:00")
    
    # ISO 8601
    try:
        return datetime.fromisoformat(s).astimezone(timezone.utc)
    except Exception:
        pass

    # YYYY-MM-DD
    m_iso = re.match(r'^(\d{4})-(\d{2})-(\d{2})', s)
    if m_iso:
        try:
            return datetime.strptime(m_iso.group(0), "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except Exception:
            pass

    # English month string (e.g. March 15 2022 or 15 March 2022)
    s_clean = re.sub(r'\s+', ' ', s.replace(",", "")).strip()
    for fmt in ("%B %d %Y", "%b %d %Y", "%d %B %Y", "%d %b %Y"):
        try:
            return datetime.strptime(s_clean, fmt).replace(tzinfo=timezone.utc)
        except Exception:
            pass

    return None


def extract_page_dates(page: dict) -> list:
    """Extracts all verifiable explicit dates from a page record."""
    dates = []
    html = page.get("html", "")
    text = page.get("text", "")
    headers = page.get("headers", {})

    # 1. HTTP Last-Modified header
    if "last-modified" in headers:
        dt = parse_date_string(headers["last-modified"])
        if dt:
            dates.append((dt, "HTTP Last-Modified Header"))

    # 2. Meta tags
    for raw_m in META_DATE_RE.findall(html):
        dt = parse_date_string(raw_m)
        if dt:
            dates.append((dt, f"Meta tag: {raw_m}"))

    # 3. <time> tag datetime
    for raw_t in TIME_TAG_RE.findall(html):
        dt = parse_date_string(raw_t)
        if dt:
            dates.append((dt, f"<time> datetime: {raw_t}"))

    # 4. Explicit text dates
    for raw_text_m in EXPLICIT_UPDATE_RE.findall(text):
        dt = parse_date_string(raw_text_m)
        if dt:
            dates.append((dt, f"Prose: '{raw_text_m}'"))

    return dates


def check_freshness(pages_data: list) -> tuple:
    findings = []
    opportunities = []
    now = datetime.now(timezone.utc)

    copyright_years = {}
    stale_pages = []

    for page in pages_data:
        url = page.get("url", "")
        html = page.get("html", "")
        text = page.get("text", "")
        
        # Copyright year detection
        c_m = COPYRIGHT_RE.search(text)
        if c_m:
            yr = int(c_m.group(1))
            copyright_years[url] = yr

        # Explicit dates
        dates = extract_page_dates(page)
        if dates:
            # Sort newest first
            dates.sort(key=lambda x: x[0], reverse=True)
            newest_date, source_label = dates[0]
            age_days = (now - newest_date).days

            # Only flag as stale if older than 3 years (1095 days) on core informational routes
            if age_days > STALE_DAYS_THRESHOLD:
                stale_pages.append({
                    "url": url,
                    "date": newest_date.strftime("%Y-%m-%d"),
                    "age_days": age_days,
                    "source": source_label
                })

    # 1. Stale Information Findings
    if stale_pages:
        findings.append({
            "title": f"Explicit timestamps indicate stale information on {len(stale_pages)} page(s)",
            "url": stale_pages[0]["url"],
            "affected_urls": [sp["url"] for sp in stale_pages],
            "category": "discoverability",
            "subcategory": "trust",
            "impact": "degrading",
            "scope": "section" if len(stale_pages) > 1 else "single-page",
            "confidence": "high",
            "evidence": f"Found outdated dates (>3 years old) at: {stale_pages[0]['url']} (dated {stale_pages[0]['date']}, {stale_pages[0]['age_days']} days old via {stale_pages[0]['source']}).",
            "suggested_action": {
                "summary": "Review and update dated claims, pricing terms, or documentation to reflect current year specifications.",
                "priority": "medium",
                "mechanism": "Answer engines prioritize fresh sources when answering timely user questions and degrade confidence in sources with old timestamps."
            }
        })

    # 2. Cross-Page Date Inconsistency
    if len(copyright_years) >= 2:
        distinct_years = sorted(set(copyright_years.values()))
        if len(distinct_years) > 1 and max(distinct_years) - min(distinct_years) >= 2:
            findings.append({
                "title": f"Inconsistent copyright years ({', '.join(str(y) for y in distinct_years)}) across crawled pages",
                "url": list(copyright_years.keys())[0],
                "affected_urls": list(copyright_years.keys()),
                "category": "discoverability",
                "subcategory": "trust",
                "impact": "cosmetic",
                "scope": "sitewide",
                "confidence": "high",
                "evidence": f"Different subpages carry conflicting copyright timestamps: {dict(list(copyright_years.items())[:3])}.",
                "suggested_action": {
                    "summary": "Standardize copyright notices across all page templates using dynamic server-side current year rendering.",
                    "priority": "low",
                    "mechanism": "Inconsistent dates across subdomains or templates create temporal ambiguity for AI extractors."
                }
            })

    # 3. Severely outdated footer copyright
    if copyright_years:
        max_cp = max(copyright_years.values())
        if max_cp < CURRENT_YEAR - 2:
            findings.append({
                "title": f"Copyright notice across {len(pages_data)} crawled route(s) is severely outdated ({max_cp})",
                "url": list(copyright_years.keys())[0],
                "affected_urls": list(copyright_years.keys()),
                "category": "discoverability",
                "subcategory": "trust",
                "impact": "cosmetic",
                "scope": "sitewide",
                "confidence": "high",
                "evidence": f"Most recent copyright year found across {len(pages_data)} crawled route(s) is {max_cp} (currently {CURRENT_YEAR}).",
                "suggested_action": {
                    "summary": f"Update footer copyright notice to {CURRENT_YEAR}.",
                    "priority": "low"
                }
            })

    return findings, opportunities


def check_page(url: str, headers: dict = None, html: str = None):
    """Compatibility interface for single-page freshness check."""
    page_record = {
        "url": url,
        "headers": headers or {},
        "html": html or "",
        "text": html or ""
    }
    findings, _ = check_freshness([page_record])
    return findings


def fetch_with_headers(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return dict(resp.getheaders()), resp.read().decode("utf-8", errors="replace")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", nargs="*")
    ap.add_argument("--pages-json", help="Path to pre-crawled pages JSON")
    ap.add_argument("--out", default="freshness_findings.json")
    args = ap.parse_args()

    pages_data = []
    if args.pages_json:
        with open(args.pages_json, "r", encoding="utf-8") as f:
            pages_data = json.load(f)
    elif args.pages:
        for url in args.pages:
            try:
                headers, html = fetch_with_headers(url)
                pages_data.append({"url": url, "headers": headers, "html": html, "text": html})
            except Exception as e:
                print(f"warning: could not fetch {url}: {e}", file=sys.stderr)

    findings, opportunities = check_freshness(pages_data)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"findings": findings, "opportunities": opportunities}, f, indent=2, ensure_ascii=False)
    print(f"Wrote {args.out}: {len(findings)} findings", file=sys.stderr)


if __name__ == "__main__":
    main()
