#!/usr/bin/env python3
"""
Local, deterministic freshness checks — comparing date signals a single page
already carries against each other and today.

Capabilities:
  1. HTTP Last-Modified header parsing (RFC 1123, RFC 850, asctime).
  2. OpenGraph & Semantic Meta Date extraction:
     - article:published_time, article:modified_time, og:updated_time, date, pubdate
  3. Visible Date Regex extraction:
     - ISO 8601 (YYYY-MM-DD), English month strings ("March 15, 2026").
  4. Evergreen Claim Staleness detection:
     - Identifies present-tense claims ("currently", "we are", "as of today")
       paired with stale dates (> 548 days old) lacking temporal qualifiers.

Usage:
    python check_freshness.py --pages https://example.com/about --out freshness_findings.json
"""
import argparse
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone

USER_AGENT = "Aura-Vision-GEO/1.0 (+read-only site audit; respects robots.txt)"
TIMEOUT = 10
STALE_DAYS = 548  # ~18 months

DATE_PATTERNS = [
    re.compile(r'\b(updated|posted|published|last updated)\s*(on)?\s*[:\-]?\s*'
               r'([A-Za-z]+ \d{1,2},? \d{4})', re.IGNORECASE),
    re.compile(r'\b(\d{4})-(\d{2})-(\d{2})\b'),
]
EVERGREEN_CLAIM_RE = re.compile(
    r'\b(we are|we\'re|currently|today,? we|our platform is|our product is)\b', re.IGNORECASE
)
AS_OF_QUALIFIER_RE = re.compile(r'\bas of\b', re.IGNORECASE)

META_DATE_RE = re.compile(
    r'<meta[^>]+(?:name|property)=["\'](?:article:published_time|article:modified_time|og:updated_time|date|last-modified|pubdate)["\'][^>]+content=["\']([^"\']+)["\']',
    re.IGNORECASE,
)


def fetch_with_headers(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return dict(resp.getheaders()), resp.read().decode("utf-8", errors="replace")


def parse_http_date(s):
    if not s:
        return None
    for fmt in (
        "%a, %d %b %Y %H:%M:%S %Z",
        "%A, %d-%b-%y %H:%M:%S %Z",
        "%a %b %d %H:%M:%S %Y",
    ):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            continue
    return None


def parse_iso_date(s):
    if not s:
        return None
    s = s.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s).astimezone(timezone.utc)
    except Exception:
        # Fallback to date part only YYYY-MM-DD
        m = re.match(r'^(\d{4}-\d{2}-\d{2})', s)
        if m:
            try:
                return datetime.strptime(m.group(1), "%Y-%m-%d").replace(tzinfo=timezone.utc)
            except Exception:
                pass
    return None


def find_visible_dates(html, text):
    found = []
    
    # 1. Meta tag dates
    for raw_date in META_DATE_RE.findall(html):
        dt = parse_iso_date(raw_date)
        if dt:
            found.append(dt)

    # 2. Textual month dates (March 15, 2026)
    for m in re.finditer(r'\b([A-Za-z]+ \d{1,2},? \d{4})\b', text):
        raw_str = m.group(1).replace(",", "")
        for fmt in ("%B %d %Y", "%b %d %Y"):
            try:
                found.append(datetime.strptime(raw_str, fmt).replace(tzinfo=timezone.utc))
                break
            except ValueError:
                pass

    # 3. ISO text dates (YYYY-MM-DD)
    for m in re.finditer(r'\b(\d{4}-\d{2}-\d{2})\b', text):
        try:
            found.append(datetime.strptime(m.group(1), "%Y-%m-%d").replace(tzinfo=timezone.utc))
        except ValueError:
            pass

    return found


def check_page(url):
    findings = []
    try:
        headers, html = fetch_with_headers(url)
    except Exception as e:
        print(f"warning: could not fetch {url}: {e}", file=sys.stderr)
        return findings

    text = re.sub(r"<[^>]+>", " ", html)
    now = datetime.now(timezone.utc)

    last_modified = parse_http_date(headers.get("Last-Modified", ""))
    visible_dates = find_visible_dates(html, text)

    all_dates = [d for d in ([last_modified] + visible_dates) if d]
    makes_evergreen_claim = bool(EVERGREEN_CLAIM_RE.search(text))
    has_as_of_qualifier = bool(AS_OF_QUALIFIER_RE.search(text))

    if all_dates:
        newest = max(all_dates)
        age_days = (now - newest).days
        if age_days > STALE_DAYS and makes_evergreen_claim and not has_as_of_qualifier:
            findings.append({
                "title": f"Evergreen-sounding claims on a page whose newest date signal is {age_days} days old",
                "category": "discoverability",
                "subcategory": "freshness",
                "impact": "degrading",
                "scope": "single-page",
                "confidence": "medium",
                "evidence": f"{url}: phrasing matched an evergreen-claim pattern (e.g. 'currently', 'we are') with no 'as of' qualifier nearby; newest date signal found on the page is {newest.date()} ({age_days} days old).",
                "suggested_action": {
                    "summary": "Either refresh the content and its date, or add an explicit 'as of <date>' qualifier so the claim doesn't read as current when it may not be.",
                    "priority": "medium",
                    "mechanism": "Assistants weight recency when deciding what to trust and repeat; an undated evergreen claim next to old date signals reads as unreliable once cross-checked.",
                },
            })
    return findings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", nargs="+", required=True)
    ap.add_argument("--out", default="freshness_findings.json")
    args = ap.parse_args()

    all_findings = []
    for url in args.pages:
        all_findings.extend(check_page(url))

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"findings": all_findings, "opportunities": []}, f, indent=2, ensure_ascii=False)
    print(f"Wrote {args.out}: {len(all_findings)} findings", file=sys.stderr)


if __name__ == "__main__":
    main()
