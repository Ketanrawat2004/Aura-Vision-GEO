#!/usr/bin/env python3
"""
Detects the gap between what a plain HTTP GET sees and what an interactive browser sees.
Strictly read-only analysis of supplied page data. Worker skills do NOT independently
fetch target pages; all page data and optional render captures are owned by the orchestrator.

Capabilities:
  1. Shared Render Analysis:
     - Analyzes rendered text captured by the orchestrator (if headless rendering was active)
       against initial HTML text without triggering redundant network requests.
  2. Empty SPA Shell Detection:
     - Identifies client-side SPA containers (#root, #app, <app-root>) where initial HTML
       is substantially empty (< 60 visible words).
  3. Framework Payload Dehydration Inspector:
     - Detects when substantive text/props live ONLY inside serialization scripts
       (__NEXT_DATA__, __NUXT_DATA__, window.__remixContext) while readable HTML markup is missing.

Usage:
    python check_render_gap.py --pages-json pages.json --out render_findings.json
"""
import argparse
import json
import re
import sys
from html.parser import HTMLParser

SPA_SHELL_PATTERNS = [
    re.compile(r'<div\s+id=["\']root["\']\s*>\s*</div>', re.IGNORECASE),
    re.compile(r'<div\s+id=["\']app["\']\s*>\s*</div>', re.IGNORECASE),
    re.compile(r'<div\s+id=["\'](root|app)["\']\s*>\s*(?:<!--.*?-->|\s*)*</div>', re.IGNORECASE),
    re.compile(r'<app-root\b[^>]*>\s*(?:<!--.*?-->|\s*)*</app-root>', re.IGNORECASE),
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

# Thresholds are calibrated across landing, docs, and blog page types:
# MIN_WORD_COUNT_THRESHOLD: only flags if empty SPA shell container (#root/#app) is present AND word count is <60
MIN_WORD_COUNT_THRESHOLD = 60
# MIN_AGNOSTIC_WORD_COUNT: strict floor for framework-agnostic SPA detection when corroborating signals exist
MIN_AGNOSTIC_WORD_COUNT = 20
# MIN_RENDERED_WORDS: ensures small error or utility pages (<30 words) don't trigger large ratio false positives
MIN_RENDERED_WORDS = 30
# RENDER_RATIO_THRESHOLD: requires 3x content expansion between raw HTML and headless render
RENDER_RATIO_THRESHOLD = 3.0

NOSCRIPT_JS_PATTERNS = [
    re.compile(r'enable\s+javascript', re.IGNORECASE),
    re.compile(r'requires?\s+javascript', re.IGNORECASE),
    re.compile(r'javascript\s+(?:is\s+)?required', re.IGNORECASE),
    re.compile(r'javascript\s+(?:must|needs?\s+to)\s+be\s+enabled', re.IGNORECASE),
    re.compile(r'turn\s+on\s+javascript', re.IGNORECASE),
    re.compile(r'need\s+javascript', re.IGNORECASE),
]


class TextExtractor(HTMLParser):
    """Minimal stdlib visible-text extractor — skips script/style/noscript/svg."""

    def __init__(self):
        super().__init__()
        self._skip_depth = 0
        self.chunks = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript", "svg"):
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "svg") and self._skip_depth > 0:
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
    try:
        p.feed(html)
    except Exception:
        pass
    return p.text()


def extract_framework_payload_words(raw_html):
    """Extracts substantive alphanumeric words from SSR/SSG JSON hydration blobs."""
    payload_texts = []
    
    for match in NEXT_DATA_RE.findall(raw_html):
        try:
            data = json.loads(match)
            payload_texts.append(json.dumps(data.get("props", {})))
        except Exception:
            pass

    for match in NUXT_DATA_RE.findall(raw_html):
        payload_texts.append(match)

    for match in REMIX_DATA_RE.findall(raw_html):
        payload_texts.append(match)

    combined = " ".join(payload_texts)
    words = re.findall(r'[a-zA-Z]{3,}', combined)
    return len(words)


def check_page(url, raw_html, precomputed_text=None, rendered_text=None):
    """
    Evaluates render gap strictly from supplied HTML and optional pre-rendered text.
    Never initiates an external network fetch.
    """
    findings, opportunities = [], []
    raw_text = precomputed_text if precomputed_text is not None else extract_visible_text(raw_html)
    raw_word_count = len(raw_text.split())
    shell_match = any(pat.search(raw_html) for pat in SPA_SHELL_PATTERNS)
    framework_words = extract_framework_payload_words(raw_html)

    if rendered_text is not None:
        rendered_word_count = len(rendered_text.split())
        ratio = (rendered_word_count / raw_word_count) if raw_word_count else float("inf")
        if ratio >= RENDER_RATIO_THRESHOLD and rendered_word_count > MIN_RENDERED_WORDS:
            ratio_desc = f"{ratio:.1f}x" if ratio != float("inf") else "significantly"
            findings.append({
                "title": f"Rendered content is {ratio_desc} larger than raw HTML at {url}",
                "url": url,
                "category": "discoverability",
                "subcategory": "render-gap",
                "impact": "blocking",
                "scope": "single-page",
                "confidence": "high",
                "evidence": f"Raw GET payload contained {raw_word_count} words; headless render produced {rendered_word_count} words.",
                "suggested_action": {
                    "summary": "Implement Server-Side Rendering (SSR) or Static Site Generation (SSG) so key content is delivered in the initial HTTP response.",
                    "priority": "high",
                    "mechanism": "Search bots and AI fetchers (e.g. GPTBot, ClaudeBot, PerplexityBot) typically perform initial evaluation on static HTML without running expensive JS rendering passes."
                },
            })
    elif shell_match and raw_word_count < MIN_WORD_COUNT_THRESHOLD:
        findings.append({
            "title": f"Client-side SPA shell detected with minimal initial HTML at {url}",
            "url": url,
            "category": "discoverability",
            "subcategory": "render-gap",
            "impact": "blocking",
            "scope": "single-page",
            "confidence": "high",
            "evidence": f"Initial HTML payload contains only {raw_word_count} visible words inside an empty SPA container element (#root/#app).",
            "suggested_action": {
                "summary": "Pre-render or server-render this route so informational content ships directly in HTML.",
                "priority": "high",
                "mechanism": "When an AI crawler fetches an empty container, it indexes an empty page and cannot answer user queries about your product or services."
            },
        })
    elif framework_words >= 50 and raw_word_count < 40:
        findings.append({
            "title": f"Substantive page content trapped inside client hydration state at {url}",
            "url": url,
            "category": "discoverability",
            "subcategory": "render-gap",
            "impact": "degrading",
            "scope": "single-page",
            "confidence": "high",
            "evidence": f"Found ~{framework_words} words serialized inside framework state scripts (__NEXT_DATA__/__NUXT_DATA__), but only {raw_word_count} words rendered into HTML tags.",
            "suggested_action": {
                "summary": "Ensure server components render content into semantic HTML markup rather than passing state purely to client-only components.",
                "priority": "medium",
                "mechanism": "AI text extraction pipelines discard <script> tags during HTML tokenization, making text in JSON blobs unsearchable."
            }
        })
    elif raw_word_count < MIN_AGNOSTIC_WORD_COUNT:
        # Path 3: Framework-agnostic client-rendered SPA detection
        # Independent of named containers (#root/#app) or hydration blobs (__NEXT_DATA__)
        # Requires raw_word_count < 20 AND at least one corroborating client-render signal:
        # (a) <noscript> tag requiring JavaScript execution
        # (b) Zero/near-zero internal links with predominantly .js/.mjs/.css asset hrefs
        corroborating_signal = None

        # Signal A: <noscript> requiring JavaScript
        for ns in re.findall(r'<noscript\b[^>]*>(.*?)</noscript>', raw_html, re.IGNORECASE | re.DOTALL):
            for pat in NOSCRIPT_JS_PATTERNS:
                if pat.search(ns):
                    clean_ns = re.sub(r'\s+', ' ', ns).strip()
                    if len(clean_ns) > 75:
                        clean_ns = clean_ns[:72] + "..."
                    corroborating_signal = f"<noscript> requirement detected (\"{clean_ns}\")"
                    break
            if corroborating_signal:
                break

        # Signal B: zero/near-zero internal links with nearly all hrefs pointing to static assets
        if not corroborating_signal:
            all_hrefs = re.findall(r'href=["\']([^"\']+)["\']', raw_html, re.IGNORECASE)
            if all_hrefs:
                asset_hrefs = [h for h in all_hrefs if re.search(r'\.(?:js|mjs|css)(?:[\?#]|$)', h, re.IGNORECASE)]
                a_hrefs = re.findall(r'<a\b[^>]*?\bhref=["\']([^"\']+)["\']', raw_html, re.IGNORECASE)
                internal_links = [
                    h for h in a_hrefs
                    if not re.match(r'^(?:[a-z]+:|\/\/|#|javascript:|mailto:|tel:)', h, re.IGNORECASE)
                ]
                if len(internal_links) <= 1 and len(asset_hrefs) >= 2 and (len(asset_hrefs) / len(all_hrefs)) >= 0.7:
                    corroborating_signal = f"zero/near-zero internal links ({len(internal_links)}) with {len(asset_hrefs)}/{len(all_hrefs)} asset bundle references (.js/.css)"

        if corroborating_signal:
            findings.append({
                "title": f"Client-rendered page has near-zero initial content with no recognized framework fingerprint at {url}",
                "url": url,
                "category": "discoverability",
                "subcategory": "render-gap",
                "impact": "blocking",
                "scope": "single-page",
                "confidence": "high",
                "evidence": f"Initial HTML payload contains only {raw_word_count} visible words with corroborating client-render signals ({corroborating_signal}), but lacks server-rendered HTML or standard framework container markers.",
                "suggested_action": {
                    "summary": "Implement Server-Side Rendering (SSR) or Static Site Generation (SSG) so key content is delivered in the initial static HTML.",
                    "priority": "high",
                    "mechanism": "AI answer engines and search bots parse raw HTML without executing client-side JavaScript bundles. Delivering an empty shell prevents AI engines from indexing or citing your content."
                },
            })

    # Signal-to-Noise Ratio (SNR) for RAG context extraction
    # Requires raw payload >120KB and at least 120 words to avoid false alarms on lightweight redirects/APIs
    raw_bytes_len = len(raw_html.encode('utf-8', errors='replace'))
    prose_bytes_len = len(raw_text.encode('utf-8', errors='replace'))
    if raw_bytes_len > 120000 and raw_word_count >= 120:
        snr = (prose_bytes_len / raw_bytes_len) * 100.0
        if snr < 3.5:
            cfi = max(1, (raw_bytes_len - prose_bytes_len) // 2048)
            findings.append({
                "title": f"Low factual Signal-to-Noise Ratio ({snr:.1f}%) causes severe RAG context dilution on {url}",
                "url": url,
                "category": "discoverability",
                "subcategory": "render-gap",
                "impact": "degrading",
                "scope": "single-page",
                "confidence": "high",
                "evidence": f"Page contains {prose_bytes_len:,} bytes of readable prose inside {raw_bytes_len:,} bytes of markup overhead ({snr:.1f}% SNR, wasting ~{cfi} RAG 512-token chunks on DOM boilerplate).",
                "suggested_action": {
                    "summary": "Reduce inline SVGs/scripts and expose clean markdown representation via /llms.txt or Content Negotiation (Accept: text/markdown).",
                    "priority": "medium",
                    "mechanism": "Answer engines chunk incoming HTML into 512-token embeddings. Low SNR dilutes information density with boilerplate, reducing semantic retrieval confidence.",
                    "fix_snippet": "# Nginx markdown content negotiation:\nif ($http_accept ~* \"text/markdown\") {\n    rewrite ^/(.*)$ /markdown/$1.md break;\n}"
                }
            })

    return findings, opportunities


def check_pages_data(pages_data):
    """Audits render gap directly from shared pages collection with zero network fetches."""
    all_findings, all_opps = [], []
    for p in pages_data:
        url = p.get("url", "")
        html = p.get("html", "")
        text = p.get("text", "")
        rendered_text = p.get("rendered_text")
        if not html:
            continue
        f, o = check_page(url, html, precomputed_text=text, rendered_text=rendered_text)
        all_findings.extend(f)
        all_opps.extend(o)
    return all_findings, all_opps


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages-json", required=True, help="Path to pre-crawled pages JSON")
    ap.add_argument("--out", default="render_findings.json")
    args = ap.parse_args()

    with open(args.pages_json, "r", encoding="utf-8") as f:
        pages_data = json.load(f)

    all_findings, all_opps = check_pages_data(pages_data)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"findings": all_findings, "opportunities": all_opps}, f, indent=2, ensure_ascii=False)
    print(f"Wrote {args.out}: {len(all_findings)} findings", file=sys.stderr)


if __name__ == "__main__":
    main()
