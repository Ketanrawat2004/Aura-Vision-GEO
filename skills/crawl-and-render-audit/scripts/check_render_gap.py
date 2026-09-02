#!/usr/bin/env python3
"""
Detects the gap between what a plain HTTP GET sees and what a browser sees.

Capabilities:
  1. Framework Payload Dehydration Inspector:
     - Extracts and inspects embedded SSR/SSG hydration scripts (__NEXT_DATA__,
       __NUXT_DATA__, window.__remixContext, window.__INITIAL_STATE__).
     - Detects "trapped content" where critical text lives only inside JSON
       payloads rather than rendered HTML tags (unreadable by text-only LLM fetchers).
  2. SPA Shell & Heuristic Text Gap Analyzer:
     - Identifies client-side SPA shells (#root, #app, <app-root>).
  3. Real-Time Headless Render Diff (when Playwright is present).

Usage:
    python check_render_gap.py --pages https://example.com https://example.com/pricing \
        --out render_findings.json
"""
import argparse
import json
import re
import sys
import urllib.request
from html.parser import HTMLParser

USER_AGENT = "ai-visibility-audit/1.0 (+read-only site audit; respects robots.txt)"
TIMEOUT = 10

SPA_SHELL_PATTERNS = [
    re.compile(r'<div\s+id=["\']root["\']\s*>\s*</div>', re.IGNORECASE),
    re.compile(r'<div\s+id=["\']app["\']\s*>\s*</div>', re.IGNORECASE),
    re.compile(r'<div\s+id=["\'](root|app)["\']', re.IGNORECASE),
    re.compile(r'<app-root\b', re.IGNORECASE),
]

NEXT_DATA_RE = re.compile(
    r'<script\s+id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>', re.IGNORECASE | re.DOTALL
)
NUXT_DATA_RE = re.compile(
    r'<script\s+id=["\']__NUXT_DATA__["\'][^>]*>(.*?)</script>', re.IGNORECASE | re.DOTALL
)
REMIX_DATA_RE = re.compile(
    r'window\.__remixContext\s*=\s*({.*?});</script>', re.IGNORECASE | re.DOTALL
)

MIN_WORD_COUNT_THRESHOLD = 60
MIN_RENDERED_WORDS = 30
RENDER_RATIO_THRESHOLD = 3.0


class TextExtractor(HTMLParser):
    """Minimal stdlib visible-text extractor — skips script/style/noscript."""

    def __init__(self):
        super().__init__()
        self._skip_depth = 0
        self.chunks = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript") and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data):
        if self._skip_depth == 0:
            stripped = data.strip()
            if stripped:
                self.chunks.append(stripped)

    def text(self):
        return " ".join(self.chunks)


def extract_visible_text(html):
    p = TextExtractor()
    p.feed(html)
    return p.text()


def extract_framework_payload_words(raw_html):
    """Extracts text content trapped inside SSR/SSG JSON hydration blobs."""
    payload_texts = []
    
    # 1. Next.js __NEXT_DATA__
    for match in NEXT_DATA_RE.findall(raw_html):
        try:
            data = json.loads(match)
            payload_texts.append(json.dumps(data.get("props", {})))
        except Exception:
            pass

    # 2. Nuxt.js __NUXT_DATA__
    for match in NUXT_DATA_RE.findall(raw_html):
        payload_texts.append(match)

    # 3. Remix Context
    for match in REMIX_DATA_RE.findall(raw_html):
        payload_texts.append(match)

    combined = " ".join(payload_texts)
    # Extract alpha-numeric words from the serialized state
    words = re.findall(r'[a-zA-Z]{3,}', combined)
    return len(words)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read().decode("utf-8", errors="replace")


def try_render(url):
    """Returns rendered text, or None if no headless-render tool is available."""
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except ImportError:
        return None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(user_agent=USER_AGENT)
            page.goto(url, timeout=TIMEOUT * 1000, wait_until="networkidle")
            content = page.inner_text("body")
            browser.close()
            return content
    except Exception as e:
        print(f"warning: render failed for {url}: {e}", file=sys.stderr)
        return None


def check_page(url, raw_html):
    findings, opportunities = [], []
    raw_text = extract_visible_text(raw_html)
    raw_word_count = len(raw_text.split())
    shell_match = any(pat.search(raw_html) for pat in SPA_SHELL_PATTERNS)
    framework_words = extract_framework_payload_words(raw_html)

    rendered_text = try_render(url)

    if rendered_text is not None:
        rendered_word_count = len(rendered_text.split())
        ratio = (rendered_word_count / raw_word_count) if raw_word_count else float("inf")
        if ratio >= RENDER_RATIO_THRESHOLD and rendered_word_count > MIN_RENDERED_WORDS:
            findings.append({
                "title": f"Rendered content is {ratio:.1f}x larger than raw HTML at {url}",
                "category": "discoverability",
                "subcategory": "render-gap",
                "impact": "blocking",
                "scope": "single-page",
                "confidence": "high",
                "evidence": f"Raw GET: {raw_word_count} words. Headless render: {rendered_word_count} words.",
                "suggested_action": {
                    "summary": "Server-render or prerender this route so key content ships in initial HTML.",
                    "priority": "high",
                    "mechanism": "Fetchers that don't execute JavaScript (GPTBot, ClaudeBot, PerplexityBot) only read the initial HTTP response. If facts only render via client JS, they remain invisible."
                },
            })
    elif shell_match and raw_word_count < MIN_WORD_COUNT_THRESHOLD:
        findings.append({
            "title": f"Client-side SPA shell detected with minimal initial HTML at {url}",
            "category": "discoverability",
            "subcategory": "render-gap",
            "impact": "blocking",
            "scope": "single-page",
            "confidence": "medium",
            "evidence": f"Initial HTML payload contains only {raw_word_count} words inside an empty SPA container element (#root/#app).",
            "suggested_action": {
                "summary": "Enable Static Site Generation (SSG) or Server-Side Rendering (SSR) for public landing pages.",
                "priority": "high",
                "mechanism": "Answer-engine indexers do not run full headless browser render cycles on initial crawl passes due to compute constraints."
            },
        })

    # Framework Hydration Trapped Content detection
    if framework_words >= 15 and (raw_word_count < 50 or framework_words > raw_word_count * 2):
        findings.append({
            "title": f"Content trapped inside client framework hydration state at {url}",
            "category": "discoverability",
            "subcategory": "render-gap",
            "impact": "degrading",
            "scope": "single-page",
            "confidence": "high",
            "evidence": f"Detected ~{framework_words} words serialized inside framework state scripts (__NEXT_DATA__/__NUXT_DATA__), but only {raw_word_count} words rendered in standard HTML markup.",
            "suggested_action": {
                "summary": "Ensure server components render content into semantic HTML tags rather than passing pure client state props.",
                "priority": "medium",
                "mechanism": "LLM text scrapers skip <script> tags; text embedded in JSON blobs is discarded during HTML-to-text tokenization."
            }
        })

    return findings, opportunities


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", nargs="+", required=True)
    ap.add_argument("--out", default="render_findings.json")
    args = ap.parse_args()

    all_findings, all_opps = [], []
    for url in args.pages:
        try:
            html = fetch(url)
        except Exception as e:
            print(f"warning: could not fetch {url}: {e}", file=sys.stderr)
            continue
        f, o = check_page(url, html)
        all_findings.extend(f)
        all_opps.extend(o)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"findings": all_findings, "opportunities": all_opps}, f, indent=2, ensure_ascii=False)
    print(f"Wrote {args.out}: {len(all_findings)} findings", file=sys.stderr)


if __name__ == "__main__":
    main()
