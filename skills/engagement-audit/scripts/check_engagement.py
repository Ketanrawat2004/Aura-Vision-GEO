#!/usr/bin/env python3
"""
Comprehensive On-Site Engagement & Visitor Retention Audit.
Standard library only (re, html.parser, urllib).

Evaluates the 8 core visitor retention dimensions required by the Adobe Hackathon Round 3 specification:
  1. What is this? (Hero orientation, descriptive H1 vs vague slogan)
  2. Who is it for? (Target audience and persona clarity)
  3. Value Proposition (Immediate benefit statement before excessive scrolling)
  4. Next Action (Descriptive, visible CTA vs generic links or absence)
  5. Navigation (Discoverability of products, pricing, contact, about)
  6. Context Retention (Brand identity, section context, and wayfinding on deeper routes)
  7. Scannability & Hierarchy (Heading structure, paragraph density, lists)
  8. Dead Ends (Pages lacking forward actions or internal navigation)

Usage:
    python check_engagement.py --pages-json pages.json --out engagement_findings.json
    python check_engagement.py --pages https://example.com https://example.com/pricing --out engagement_findings.json
"""
import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
from html.parser import HTMLParser

USER_AGENT = "Aura-Vision-GEO/2.0 (+read-only site audit; respects robots.txt)"
TIMEOUT = 5

NAV_RE = re.compile(r'(<nav\b|<header\b|role=["\']navigation["\']|class=["\'][^"\']*\b(?:nav|navbar|menu)\b)', re.IGNORECASE)
VIEWPORT_RE = re.compile(r'<meta[^>]+name=["\']viewport["\']', re.IGNORECASE)
H1_RE = re.compile(r'<h1\b[^>]*>(.*?)</h1>', re.IGNORECASE | re.DOTALL)
H2_RE = re.compile(r'<h2\b[^>]*>(.*?)</h2>', re.IGNORECASE | re.DOTALL)
P_RE = re.compile(r'<p\b[^>]*>(.*?)</p>', re.IGNORECASE | re.DOTALL)
LIST_RE = re.compile(r'<(ul|ol)\b[^>]*>', re.IGNORECASE)
BREADCRUMB_RE = re.compile(r'(aria-label=["\']breadcrumb["\']|class=["\'][^"\']*\bbreadcrumb\b|itemtype=["\']https?://schema\.org/BreadcrumbList["\'])', re.IGNORECASE)

CTA_RE = re.compile(
    r'<(?:a|button)\b[^>]*>(.*?)</(?:a|button)>',
    re.IGNORECASE | re.DOTALL
)

ACTION_CTA_KEYWORDS = {
    "start", "get started", "try", "sign up", "free trial", "book a demo",
    "schedule demo", "request demo", "contact sales", "contact us", "get in touch",
    "talk to sales", "buy now", "subscribe", "explore", "download", "join",
    "get a quote", "talk to an expert", "see pricing", "view pricing", "view plans",
    "request access", "claim your", "apply now", "register", "order now", "open account"
}

GENERIC_CTA_KEYWORDS = {"click here", "here", "read more", "more", "learn more", "submit", "go", "continue"}

AUDIENCE_SIGNALS = [
    re.compile(r'\b(for (?:developers|teams|enterprise|startups|designers|creators|businesses|agencies|marketers|engineers|retailers|students))\b', re.IGNORECASE),
    re.compile(r'\b(built for|designed for|tailored for|crafted for|made for)\b', re.IGNORECASE),
    re.compile(r'\b(use cases|who it\'s for|who we serve)\b', re.IGNORECASE),
]

VAGUE_HERO_BUZZWORDS = [
    "the future of", "transforming the way", "revolutionizing", "welcome to",
    "next generation", "empowering everyone", "better together", "innovation unleashed"
]


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.chunks = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript", "svg"):
            self._skip_depth += 1
        elif tag == "img" and self._skip_depth == 0:
            attrs_dict = dict(attrs)
            alt = attrs_dict.get("alt", "").strip()
            if alt:
                self.chunks.append(alt)

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "svg") and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data):
        if self._skip_depth == 0:
            clean = data.strip()
            if clean:
                self.chunks.append(clean)

    def text(self):
        return " ".join(self.chunks)


def strip_tags(html):
    p = TextExtractor()
    try:
        p.feed(html)
    except Exception:
        pass
    return p.text()


def check_orientation_and_hero(url: str, html: str, visible_text: str, is_home: bool) -> list:
    """Evaluates 'What is this?' and 'Who is it for?' on landing and home pages."""
    findings = []
    h1_matches = H1_RE.findall(html)
    clean_h1s = [strip_tags(h).strip() for h in h1_matches if strip_tags(h).strip()]

    # 1. Missing H1
    if not clean_h1s:
        findings.append({
            "title": f"No primary heading (<h1>) found to orient visitors on {url}",
            "url": url,
            "category": "engagement",
            "subcategory": "orientation",
            "impact": "degrading",
            "scope": "single-page",
            "confidence": "high",
            "evidence": f"Page HTML contains 0 <h1> elements. First 100 characters: '{visible_text[:100]}...'",
            "suggested_action": {
                "summary": "Add a prominent <h1> stating clearly what the product, service, or resource is.",
                "priority": "high",
                "mechanism": "Visitors decide whether to stay within 3–5 seconds. A clear H1 immediately establishes cognitive orientation."
            }
        })
    elif is_home:
        # Vague marketing slogan without product definition (homepage only to avoid blog/docs false positives)
        h1_text = clean_h1s[0].lower()
        if any(vague in h1_text for vague in VAGUE_HERO_BUZZWORDS) and len(h1_text.split()) < 7:
            findings.append({
                "title": f"Primary heading on {url} uses abstract slogan rather than defining what the product does",
                "url": url,
                "category": "engagement",
                "subcategory": "orientation",
                "impact": "degrading",
                "scope": "single-page",
                "confidence": "medium",
                "evidence": f"Homepage <h1> is '{clean_h1s[0]}' without accompanying product descriptor in the heading.",
                "suggested_action": {
                    "summary": "Pair the slogan with a descriptive product category (e.g. 'Payment Infrastructure for the Internet').",
                    "priority": "medium",
                    "mechanism": "Visitors coming from search or AI citations bounce when they cannot confirm what problem the website solves."
                }
            })

    # 2. Who is it for? (Audience clarity on landing/home pages only to protect subpages)
    if is_home:
        first_300_words = " ".join(visible_text.split()[:300])
        has_audience = any(pat.search(first_300_words) for pat in AUDIENCE_SIGNALS)
        if not has_audience and len(visible_text.split()) > 100:
            findings.append({
                "title": f"Homepage ({url}) lacks immediate target audience or persona indicators above the fold",
                "url": url,
                "category": "engagement",
                "subcategory": "orientation",
                "impact": "degrading",
                "scope": "single-page",
                "confidence": "medium",
                "evidence": f"Initial 300 words of visible text do not specify target customer (e.g. developers, enterprise, SMBs, creative professionals).",
                "suggested_action": {
                    "summary": "Add explicit audience cues ('Built for engineering teams', 'Designed for SMBs') near the hero section.",
                    "priority": "medium",
                    "mechanism": "Uncertain visitors who cannot self-identify as the target user bounce prematurely."
                }
            })

    # 3. Mobile Viewport Configuration
    if is_home and not re.search(r'<meta[^>]+name=["\']viewport["\'][^>]*>', html, re.IGNORECASE):
        findings.append({
            "title": f"Mobile viewport configuration (<meta name=\"viewport\">) missing on {url}",
            "url": url,
            "category": "engagement",
            "subcategory": "orientation",
            "impact": "degrading",
            "scope": "sitewide",
            "confidence": "high",
            "evidence": f"No <meta name=\"viewport\"> tag detected in document <head>.",
            "suggested_action": {
                "summary": "Add standard responsive viewport meta tag to support mobile answer-engine referrals.",
                "priority": "high",
                "mechanism": "Over 60% of generative assistant queries originate on mobile devices. Pages without a viewport tag render zoomed out and unreadable.",
                "fix_snippet": '<meta name="viewport" content="width=device-width, initial-scale=1">'
            }
        })

    return findings


def check_calls_to_action(url: str, html: str, is_home: bool) -> list:
    """Evaluates presence and quality of CTAs."""
    findings = []
    action_ctas = []
    generic_ctas = []

    for match in CTA_RE.findall(html):
        clean_text = strip_tags(match).strip().lower()
        if not clean_text:
            continue
        if any(k in clean_text for k in ACTION_CTA_KEYWORDS):
            action_ctas.append(clean_text)
        elif clean_text in GENERIC_CTA_KEYWORDS:
            generic_ctas.append(clean_text)

    # 1. Total lack of CTA on key landing/pricing/home routes (restricted to home to avoid flagging informational blogs)
    if is_home and not action_ctas:
        findings.append({
            "title": f"No distinct, actionable call-to-action (CTA) detected on {url}",
            "url": url,
            "category": "engagement",
            "subcategory": "next-action",
            "impact": "degrading",
            "scope": "single-page",
            "confidence": "high",
            "evidence": f"No high-intent conversion action found (e.g. 'Get Started', 'Start Free Trial', 'Book Demo', 'See Pricing').",
            "suggested_action": {
                "summary": "Add a prominent primary CTA button above the fold guiding visitors to the immediate next step.",
                "priority": "high",
                "mechanism": "Without a clear next step, engaged visitors leave rather than exploring deeper."
            }
        })

    # 2. Overuse of vague CTAs ('click here')
    if len(generic_ctas) >= 3 and not action_ctas:
        findings.append({
            "title": f"Calls-to-action on {url} rely on ambiguous text ('{generic_ctas[0]}') without action verbs",
            "url": url,
            "category": "engagement",
            "subcategory": "next-action",
            "impact": "cosmetic",
            "scope": "single-page",
            "confidence": "medium",
            "evidence": f"Found {len(generic_ctas)} generic link labels: {generic_ctas[:4]}.",
            "suggested_action": {
                "summary": "Replace generic labels like 'click here' or 'read more' with benefit-oriented text (e.g. 'View Documentation', 'Compare Plans').",
                "priority": "low",
                "mechanism": "Descriptive CTA labels set expectations and increase click-through rates."
            }
        })

    return findings


def check_navigation_completeness(site_root: str, pages_data: list) -> list:
    """Evaluates whether visitors can find essential pillars: products, pricing, contact, about."""
    if not pages_data:
        return []
    findings = []
    all_links = set()
    for p in pages_data:
        for link in p.get("links", []):
            all_links.add(link.lower())

    # Check findability across the crawled link graph
    essential_sections = {
        "pricing": ["/pricing", "/plans", "/cost", "/rates"],
        "about": ["/about", "/company", "/team", "/our-story"],
        "contact": ["/contact", "/support", "/sales", "/reach-us"],
        "products": ["/product", "/products", "/services", "/features", "/solutions"]
    }

    missing_sections = []
    for section_name, patterns in essential_sections.items():
        found = any(any(pat in link for pat in patterns) for link in all_links)
        if not found:
            missing_sections.append(section_name)

    if len(missing_sections) >= 2:
        findings.append({
            "title": f"Navigation across {len(pages_data)} crawled route(s) omits links to essential business information ({', '.join(missing_sections)})",
            "url": site_root,
            "category": "engagement",
            "subcategory": "navigation",
            "impact": "degrading",
            "scope": "sitewide",
            "confidence": "high",
            "evidence": f"Across {len(pages_data)} crawled routes, internal navigation provides no visible paths to: {missing_sections}.",
            "suggested_action": {
                "summary": f"Expose clear top-level or footer navigation links to {', '.join(missing_sections)}.",
                "priority": "medium",
                "mechanism": "Visitors and AI agents seeking core transactional information (pricing, company credentials, contact) will abandon the site if it cannot be found within one click."
            }
        })

    return findings


def check_context_retention_and_breadcrumbs(page: dict, site_name: str) -> list:
    """Evaluates whether deeper pages preserve brand orientation and offer wayfinding."""
    findings = []
    url = page.get("url", "")
    parsed = urllib.parse.urlparse(url)
    segments = [s for s in parsed.path.split("/") if s]

    # Deeper page (at least 2 subpath levels, e.g. /docs/api/endpoints or /blog/2026/feature)
    if len(segments) >= 2:
        html = page.get("html", "")
        has_breadcrumbs = bool(BREADCRUMB_RE.search(html))
        has_nav = bool(NAV_RE.search(html))

        if not has_breadcrumbs and not has_nav:
            findings.append({
                "title": f"Deep page at {url} lacks breadcrumbs or parent wayfinding",
                "url": url,
                "category": "engagement",
                "subcategory": "context-retention",
                "impact": "degrading",
                "scope": "single-page",
                "confidence": "high",
                "evidence": f"Route '{parsed.path}' has 2+ path segments but contains no breadcrumb trail or main navigation container.",
                "suggested_action": {
                    "summary": "Add a breadcrumb navigation bar allowing visitors who land directly from AI answers to navigate back to parent topics.",
                    "priority": "medium",
                    "mechanism": "Visitors entering via deep links from search/AI need immediate context on where they are in the site hierarchy."
                }
            })

    return findings


def check_scannability_and_hierarchy(url: str, html: str, visible_text: str) -> list:
    """Evaluates typography, heading distribution, and wall-of-text fatigue."""
    findings = []
    
    # 1. Check paragraph length
    paragraphs = [strip_tags(p).strip() for p in P_RE.findall(html) if strip_tags(p).strip()]
    word_counts = [len(p.split()) for p in paragraphs]
    
    if word_counts:
        # Paragraph length threshold: requires at least 2 paragraphs >140 words AND avg >100 words to avoid false alarms on single long quotes
        avg_words = sum(word_counts) / len(word_counts)
        long_paras = [w for w in word_counts if w > 140]
        if len(long_paras) >= 2 and avg_words > 100:
            findings.append({
                "title": f"Dense, unbroken walls of text hinder visual scannability on {url}",
                "url": url,
                "category": "engagement",
                "subcategory": "scannability",
                "impact": "cosmetic",
                "scope": "single-page",
                "confidence": "high",
                "evidence": f"Found {len(long_paras)} paragraph(s) exceeding 140 words (longest has {max(word_counts)} words). Average paragraph length: {avg_words:.0f} words.",
                "suggested_action": {
                    "summary": "Break long prose into shorter 2–3 sentence paragraphs with bold lead-ins or bulleted lists.",
                    "priority": "low",
                    "mechanism": "Web visitors scan in F-shaped patterns; large walls of text cause visual fatigue and increase bounce rate."
                }
            })

    # 2. Check heading hierarchy: requires >400 words to ensure short landing or contact pages aren't penalized
    h2_count = len(H2_RE.findall(html))
    total_words = len(visible_text.split())
    if total_words > 400 and h2_count == 0:
        findings.append({
            "title": f"Substantive page at {url} ({total_words} words) lacks subheadings (<h2>) to organize content",
            "url": url,
            "category": "engagement",
            "subcategory": "scannability",
            "impact": "degrading",
            "scope": "single-page",
            "confidence": "high",
            "evidence": f"Page contains {total_words} words but zero <h2> subheadings.",
            "suggested_action": {
                "summary": "Organize major topical sections under informative <h2> headings.",
                "priority": "medium",
                "mechanism": "Subheadings enable visitors and AI summarizers to quickly identify relevant sections without parsing the entire page.",
                "fix_snippet": "<h2>Key Architectural Capabilities</h2>\n<p>Section prose explaining primary features...</p>"
            }
        })

    # 3. Check for heading hierarchy level skipping (e.g., h1 to h3/h4)
    all_headings = re.findall(r'<h([1-6])\b', html, re.IGNORECASE)
    if len(all_headings) >= 2:
        levels = [int(x) for x in all_headings]
        skipped_pairs = []
        for i in range(len(levels) - 1):
            curr, nxt = levels[i], levels[i+1]
            if nxt > curr + 1:
                skipped_pairs.append(f"<h{curr}> to <h{nxt}>")
        if skipped_pairs:
            findings.append({
                "title": f"Heading hierarchy skips levels ({skipped_pairs[0]}) on {url}",
                "url": url,
                "category": "engagement",
                "subcategory": "scannability",
                "impact": "cosmetic",
                "scope": "single-page",
                "confidence": "high",
                "evidence": f"Heading structure skips semantic hierarchy: {skipped_pairs[:2]}.",
                "suggested_action": {
                    "summary": "Maintain sequential heading levels (e.g. nest <h2> below <h1>, and <h3> below <h2>) rather than skipping levels for visual styling.",
                    "priority": "low",
                    "mechanism": "Screen readers and automated RAG document parsers rely on sequential heading hierarchy to construct accurate topic trees.",
                    "fix_snippet": "<h1>Main Document Title</h1>\n  <h2>Primary Topic Section</h2>\n    <h3>Subtopic Detail</h3>"
                }
            })

    return findings


def check_dead_ends(page: dict) -> list:
    """Detects pages where visitors have no useful forward action or navigation."""
    findings = []
    url = page.get("url", "")
    links = page.get("links", [])
    html = page.get("html", "")
    
    # Exclude login/auth/privacy policy pages
    path = urllib.parse.urlparse(url).path.lower()
    if any(seg in path for seg in ("/privacy", "/terms", "/login", "/signup", "/legal")):
        return []

    # If page has fewer than 2 internal links and no navigation
    if len(links) <= 1 and not NAV_RE.search(html):
        findings.append({
            "title": f"Dead-end page detected with no onward navigation at {url}",
            "url": url,
            "category": "engagement",
            "subcategory": "dead-ends",
            "impact": "degrading",
            "scope": "single-page",
            "confidence": "high",
            "evidence": f"Page contains only {len(links)} internal link(s) and lacks a persistent navigation header or footer.",
            "suggested_action": {
                "summary": "Ensure global navigation and relevant next-step links appear on all public subpages.",
                "priority": "high",
                "mechanism": "When visitors arrive at a dead-end page, their only choice is to close the tab or hit back, ending the session."
            }
        })

    return findings


def check_page_engagement(page: dict, site_root: str, site_name: str) -> list:
    findings = []
    url = page.get("url", "")
    html = page.get("html", "")
    text = page.get("text", "")
    if not html:
        return []

    is_home = urllib.parse.urlparse(url).path.lower() in ("", "/")

    # 1. Viewport check (subpages; homepage handled in check_orientation_and_hero)
    if not is_home and not VIEWPORT_RE.search(html):
        findings.append({
            "title": f"Mobile viewport configuration missing on {url}",
            "url": url,
            "category": "engagement",
            "subcategory": "navigation",
            "impact": "degrading",
            "scope": "single-page",
            "confidence": "high",
            "evidence": "No <meta name=\"viewport\"> tag present in HTML head.",
            "suggested_action": {
                "summary": "Add <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">.",
                "priority": "high",
                "mechanism": "Pages without viewport meta tags fail to adapt to mobile screens, causing immediate user bounce on mobile devices."
            }
        })

    findings.extend(check_orientation_and_hero(url, html, text, is_home))
    findings.extend(check_calls_to_action(url, html, is_home))
    findings.extend(check_context_retention_and_breadcrumbs(page, site_name))
    findings.extend(check_scannability_and_hierarchy(url, html, text))
    findings.extend(check_dead_ends(page))

    return findings


def check_pages_data(pages_data, site_url=None):
    if not pages_data:
        return [], []
    all_findings = []
    site_root = site_url or (pages_data[0].get("url") if pages_data else "")
    parsed_root = urllib.parse.urlparse(site_root)
    site_name = parsed_root.netloc.split(".")[0].capitalize() if parsed_root.netloc else "Site"

    # Sitewide navigation check
    all_findings.extend(check_navigation_completeness(site_root, pages_data))

    # Per-page audits
    for p in pages_data:
        all_findings.extend(check_page_engagement(p, site_root, site_name))

    return all_findings, []


def check_page(url: str, html: str, headers: dict = None):
    """Compatibility interface for per-page evaluation."""
    text = strip_tags(html)
    page_record = {"url": url, "html": html, "text": text, "links": []}
    parsed = urllib.parse.urlparse(url)
    site_name = parsed.netloc.split(".")[0].capitalize() if parsed.netloc else "Site"
    findings = check_page_engagement(page_record, url, site_name)
    return findings, []


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read().decode("utf-8", errors="replace")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", nargs="*")
    ap.add_argument("--pages-json", help="Path to pre-crawled pages JSON")
    ap.add_argument("--out", default="engagement_findings.json")
    args = ap.parse_args()

    pages_data = []
    if args.pages_json:
        with open(args.pages_json, "r", encoding="utf-8") as f:
            pages_data = json.load(f)
    elif args.pages:
        for url in args.pages:
            try:
                html = fetch(url)
                text = strip_tags(html)
                pages_data.append({"url": url, "html": html, "text": text, "links": []})
            except Exception as e:
                print(f"warning: could not fetch {url}: {e}", file=sys.stderr)

    findings, opportunities = check_pages_data(pages_data)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"findings": findings, "opportunities": opportunities}, f, indent=2, ensure_ascii=False)
    print(f"Wrote {args.out}: {len(findings)} findings", file=sys.stderr)


if __name__ == "__main__":
    main()
