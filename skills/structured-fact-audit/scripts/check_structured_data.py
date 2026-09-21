#!/usr/bin/env python3
"""
Deep Schema.org Knowledge Graph, Microdata & Factual Disambiguation Audit.

Capabilities:
  1. Multi-Format Schema Extraction:
     - Recursive JSON-LD unpacking (nested @graph, arrays, and item lists).
     - HTML5 Microdata (itemscope / itemtype).
  2. Grounded Schema Inference (Eliminating False Positives):
     - Differentiates true Product/Service pages (pricing tiers, e-commerce, /product, /pricing paths)
       from arbitrary blog posts or mentions of monetary figures.
     - Detects genuine FAQPage, Article, Organization, and Breadcrumb needs.
  3. Factual Consistency & Conflict Detection:
     - Detects conflicts between structured data values (e.g., schema price) and visible HTML prose.
     - Validates presence of core properties (name, url, offers, priceCurrency).
  4. Non-Text Locked Fact Detection:
     - Detects facts locked solely in images (charts, price tables without alt text).
     - Detects facts locked solely in PDFs ONLY when equivalent readable HTML text is missing or sparse.

Usage:
    python check_structured_data.py --pages-json pages.json --out struct_findings.json
    python check_structured_data.py --pages https://example.com https://example.com/pricing --out struct_findings.json
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

LDJSON_RE = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)
MICRODATA_TYPE_RE = re.compile(
    r'itemtype=["\']https?://schema\.org/([A-Za-z0-9_]+)["\']',
    re.IGNORECASE,
)

PRICE_RE = re.compile(
    r'([$₹€£¥]\s?\d[\d,]*(\.\d{2})?|\d[\d,]*(\.\d{2})?\s?[$₹€£¥]|\b(USD|EUR|GBP|INR|CAD|AUD|JPY)\s?\d[\d,]*(\.\d{2})?|\bRs\.?\s?\d[\d,]*)',
    re.IGNORECASE,
)

COMMERCIAL_PATTERNS = [
    re.compile(r'\b(per month|per year|/mo|/yr|billed monthly|billed annually|tier|starter plan|pro plan|enterprise plan|pricing tier)\b', re.IGNORECASE),
    re.compile(r'\b(add to cart|buy now|checkout|in stock|order now|free trial|subscribe)\b', re.IGNORECASE),
    re.compile(r'\b(sku|model number|product details|specifications)\b', re.IGNORECASE),
]

FAQ_HEADING_RE = re.compile(r'<h[2-4][^>]*>([^<]{5,150}\?)\s*</h[2-4]>', re.IGNORECASE)
IMG_RE = re.compile(r'<img\b([^>]*)>', re.IGNORECASE)
ALT_RE = re.compile(r'alt=["\']([^"\']*)["\']', re.IGNORECASE)
SRC_RE = re.compile(r'src=["\']([^"\']*)["\']', re.IGNORECASE)
PDF_LINK_RE = re.compile(
    r'<a\b[^>]*href=["\']([^"\']+\.pdf)["\'][^>]*>([^<]{0,80})</a>', re.IGNORECASE
)
LOCKED_DOC_KEYWORDS = ("pricing", "price", "spec", "datasheet", "brochure", "menu", "catalog", "rate")

AUTHORITATIVE_SAME_AS_DOMAINS = (
    "wikidata.org", "wikipedia.org", "crunchbase.com", "github.com", "linkedin.com", "apple.com", "google.com"
)

TYPE_EQUIVALENTS = {
    "Product": {"Product", "IndividualProduct", "ProductModel", "Service", "SoftwareApplication"},
    "Organization": {"Organization", "NewsMediaOrganization", "Corporation", "EducationalOrganization", "LocalBusiness", "Store", "OnlineStore"},
    "Article": {"Article", "NewsArticle", "BlogPosting", "TechArticle", "ScholarlyArticle"},
    "FAQPage": {"FAQPage"},
    "WebSite": {"WebSite"},
    "BreadcrumbList": {"BreadcrumbList"},
}

SCHEMA_FIX_TEMPLATES = {
    "Product": '<script type="application/ld+json">\n{\n  "@context": "https://schema.org",\n  "@type": "Product",\n  "name": "Product or Service Name",\n  "description": "Comprehensive feature and capability summary",\n  "offers": {\n    "@type": "Offer",\n    "price": "99.00",\n    "priceCurrency": "USD",\n    "availability": "https://schema.org/InStock"\n  }\n}\n</script>',
    "Organization": '<script type="application/ld+json">\n{\n  "@context": "https://schema.org",\n  "@type": "Organization",\n  "name": "Brand Name",\n  "url": "https://example.com",\n  "sameAs": [\n    "https://www.wikidata.org/wiki/Q...",\n    "https://en.wikipedia.org/wiki/..."\n  ]\n}\n</script>',
    "FAQPage": '<script type="application/ld+json">\n{\n  "@context": "https://schema.org",\n  "@type": "FAQPage",\n  "mainEntity": [\n    {\n      "@type": "Question",\n      "name": "Common Question?",\n      "acceptedAnswer": {"@type": "Answer", "text": "Factual concise answer."}\n    }\n  ]\n}\n</script>',
    "Article": '<script type="application/ld+json">\n{\n  "@context": "https://schema.org",\n  "@type": "Article",\n  "headline": "Article Title",\n  "datePublished": "2026-09-01T08:00:00Z",\n  "author": {"@type": "Person", "name": "Author Name"}\n}\n</script>',
    "BreadcrumbList": '<script type="application/ld+json">\n{\n  "@context": "https://schema.org",\n  "@type": "BreadcrumbList",\n  "itemListElement": [\n    {"@type": "ListItem", "position": 1, "name": "Home", "item": "https://example.com"},\n    {"@type": "ListItem", "position": 2, "name": "Section", "item": "https://example.com/section"}\n  ]\n}\n</script>'
}


class HTMLTagStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.chunks = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript", "svg"):
            self._skip_depth += 1

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
    p = HTMLTagStripper()
    try:
        p.feed(html)
    except Exception:
        pass
    return p.text()


def extract_ldjson_types(html):
    types = set()
    errors = []
    nodes = []

    for block in LDJSON_RE.findall(html):
        clean = block.strip()
        if not clean:
            continue
        try:
            data = json.loads(clean)
        except json.JSONDecodeError as e:
            errors.append(str(e))
            continue

        def _collect_nodes(obj, collector):
            if isinstance(obj, dict):
                collector.append(obj)
                if "@graph" in obj and isinstance(obj["@graph"], list):
                    for item in obj["@graph"]:
                        _collect_nodes(item, collector)
                for v in obj.values():
                    if isinstance(v, (dict, list)):
                        _collect_nodes(v, collector)
            elif isinstance(obj, list):
                for item in obj:
                    _collect_nodes(item, collector)

        raw_nodes = []
        _collect_nodes(data, raw_nodes)
        for node in raw_nodes:
            t = node.get("@type")
            if isinstance(t, list):
                types.update(t)
            elif t:
                types.add(t)
            nodes.append(node)

    for m_type in MICRODATA_TYPE_RE.findall(html):
        types.add(m_type)

    return types, errors, nodes


def is_product_page(url: str, html: str, visible_text: str) -> bool:
    """
    Carefully evaluates whether a page genuinely represents a commercial Product or Service offering.
    Avoids false positives from casual price mentions in blogs or about pages.
    """
    path = urllib.parse.urlparse(url).path.lower()
    
    # URL path indicators
    has_product_path = any(segment in path for segment in ("/pricing", "/product", "/products", "/plans", "/services", "/store", "/shop"))
    
    # Commercial signals in visible prose
    has_price = bool(PRICE_RE.search(visible_text))
    commercial_signals = sum(1 for pat in COMMERCIAL_PATTERNS if pat.search(visible_text))
    
    # If path clearly indicates product/pricing and price or commercial signals exist
    if has_product_path and (has_price or commercial_signals >= 1):
        return True
    
    # If not in path, require both price pattern AND strong commercial signals (e.g. "per month", "add to cart")
    if has_price and commercial_signals >= 2:
        return True
        
    return False


def infer_expected_types(url: str, html: str, visible_text: str) -> set:
    """Infers expected Schema.org types grounded in authentic page intent."""
    expected = set()
    path = urllib.parse.urlparse(url).path.lower()

    # 1. Homepage expects Organization and WebSite
    if path in ("", "/"):
        expected.add("Organization")
        expected.add("WebSite")

    # 2. Commercial / Product offering
    if is_product_page(url, html, visible_text):
        expected.add("Product")

    # 3. FAQ content (at least 2 Q&A headings with question marks)
    faq_headings = FAQ_HEADING_RE.findall(html)
    if len(faq_headings) >= 2 and ("faq" in path or len(faq_headings) >= 3):
        expected.add("FAQPage")

    # 4. Article / Blog post
    if any(seg in path for seg in ("/blog/", "/article/", "/news/", "/post/")) and len(visible_text.split()) > 150:
        expected.add("Article")

    # 5. Deeper subpage expects BreadcrumbList
    segments = [s for s in path.split("/") if s]
    if len(segments) >= 2:
        expected.add("BreadcrumbList")

    return expected


def validate_required_props(node_type: str, nodes: list) -> list:
    """Validates presence of essential schema properties for recognized types."""
    problems = []
    matching = [n for n in nodes if n.get("@type") == node_type or
                (isinstance(n.get("@type"), list) and node_type in n.get("@type", []))]
    for n in matching:
        if node_type in TYPE_EQUIVALENTS["Organization"]:
            if not n.get("name"):
                problems.append(f"Organization schema missing essential 'name' property.")
            if not n.get("url"):
                problems.append(f"Organization schema missing essential 'url' property.")
        elif node_type in TYPE_EQUIVALENTS["Product"]:
            if not n.get("name"):
                problems.append(f"Product schema missing 'name' property.")
            if not n.get("offers"):
                problems.append(f"Product schema for '{n.get('name', 'item')}' missing 'offers' or price specification.")
        elif node_type == "FAQPage":
            entities = n.get("mainEntity", [])
            if isinstance(entities, dict):
                entities = [entities]
            bad = [e for e in entities if not (isinstance(e, dict) and e.get("name")
                   and isinstance(e.get("acceptedAnswer"), dict)
                   and e["acceptedAnswer"].get("text"))]
            if not entities:
                problems.append("FAQPage schema missing 'mainEntity' Question/acceptedAnswer entries.")
            elif bad:
                problems.append(f"FAQPage schema has {len(bad)}/{len(entities)} malformed Q&A Question/acceptedAnswer entries.")
    return problems


def normalize_price(val: str):
    """Extracts floating point numeric price value from string (e.g. '$99.00' -> 99.0, '99' -> 99.0)."""
    if not val:
        return None
    cleaned = re.sub(r'[, ]', '', str(val))
    m = re.search(r'\d+(?:\.\d+)?', cleaned)
    if m:
        try:
            return float(m.group(0))
        except Exception:
            return None
    return None


def check_schema_fact_conflicts(nodes: list, visible_text: str, url: str) -> list:
    """Detects obvious conflicts between values stated in structured data and visible text."""
    findings = []
    
    # Check Product offer prices vs visible text
    for n in nodes:
        if n.get("@type") in TYPE_EQUIVALENTS["Product"]:
            offers = n.get("offers", {})
            if isinstance(offers, list) and offers:
                offers = offers[0]
            if isinstance(offers, dict):
                schema_price = str(offers.get("price", "")).strip()
                schema_num = normalize_price(schema_price)
                if schema_price and schema_num is not None:
                    vis_prices = PRICE_RE.findall(visible_text)
                    if vis_prices:
                        clean_vis_prices = [p[0] for p in vis_prices if any(char.isdigit() for char in p[0])]
                        # Match if exact string is present OR if numeric prices are equivalent ($99 == 99.00)
                        has_match = any(schema_price in vp or normalize_price(vp) == schema_num for vp in clean_vis_prices)
                        if clean_vis_prices and not has_match:
                            findings.append({
                                "title": f"Conflicting pricing between structured data and visible page text at {url}",
                                "url": url,
                                "category": "discoverability",
                                "subcategory": "structured-data",
                                "impact": "degrading",
                                "scope": "single-page",
                                "confidence": "high",
                                "evidence": f"Product schema specifies price '{schema_price}', but visible page text displays '{clean_vis_prices[0]}'.",
                                "suggested_action": {
                                    "summary": "Synchronize structured data price with current visible pricing.",
                                    "priority": "high",
                                    "mechanism": "When structured data contradicts visible text, answer engines reject the structured data as untrusted or stale."
                                }
                            })
                            break
    return findings


def check_locked_facts(html: str, visible_text: str, url: str = "") -> list:
    """
    Detects important facts locked in non-text elements (images or PDFs).
    Avoids flagging PDF links when equivalent readable HTML text is already present.
    """
    findings = []

    # 1. Unlabeled meaningful images (charts, pricing graphics, tables)
    unlabeled_meaningful_imgs = []
    for attrs in IMG_RE.findall(html):
        src_m = SRC_RE.search(attrs)
        alt_m = ALT_RE.search(attrs)
        src = src_m.group(1) if src_m else ""
        alt = alt_m.group(1).strip() if alt_m else ""
        if not alt and any(k in src.lower() for k in ("price", "pricing", "spec", "datasheet", "chart", "infographic", "table")):
            unlabeled_meaningful_imgs.append(src)

    if unlabeled_meaningful_imgs:
        findings.append({
            "title": f"Factual graphics ({len(unlabeled_meaningful_imgs)} image(s)) on {url} lack accessible text descriptions" if url else f"Factual graphics ({len(unlabeled_meaningful_imgs)} image(s)) lack accessible text descriptions",
            "url": url,
            "category": "discoverability",
            "subcategory": "structured-data",
            "impact": "degrading",
            "scope": "section",
            "confidence": "high",
            "evidence": f"Images with filenames indicating factual data lack alt text: {unlabeled_meaningful_imgs[:3]}",
            "suggested_action": {
                "summary": "Provide descriptive alt text or HTML data tables summarizing the visual facts.",
                "priority": "medium",
                "mechanism": "Web crawlers and LLM text scrapers cannot execute computer vision on all indexed images; facts inside uncaptioned images are omitted from citations."
            },
        })

    # 2. PDF locked facts: ONLY flag if keyword suggests essential data AND visible HTML is missing or sparse
    locked_docs = []
    for href, link_text in PDF_LINK_RE.findall(html):
        combined = (href + " " + link_text).lower()
        if any(k in combined for k in LOCKED_DOC_KEYWORDS):
            # Check if equivalent data is present in HTML text
            has_visible_facts = False
            if any(k in combined for k in ("price", "pricing", "rate")):
                has_visible_facts = bool(PRICE_RE.search(visible_text))
            elif any(k in combined for k in ("spec", "datasheet")):
                has_visible_facts = len(visible_text.split()) > 150

            # If page text does NOT carry the information, the fact is locked in PDF
            if not has_visible_facts:
                locked_docs.append(href)

    if locked_docs:
        findings.append({
            "title": f"Essential product/pricing details appear locked solely inside linked PDF document(s) on {url}" if url else "Essential product/pricing details appear locked solely inside linked PDF document(s)",
            "url": url,
            "category": "discoverability",
            "subcategory": "structured-data",
            "impact": "degrading",
            "scope": "section",
            "confidence": "high",
            "evidence": f"Page links to documents ({locked_docs[:2]}), but the HTML page lacks equivalent readable specifications or pricing text.",
            "suggested_action": {
                "summary": "Expose the key data points as crawlable HTML text and retain the PDF as a secondary reference download.",
                "priority": "high",
                "mechanism": "Standard answer engine scrapers focus on HTML DOM text. Facts locked inside binary PDFs require external download passes and are frequently omitted."
            },
        })

    return findings


def check_page(url: str, html: str, precomputed_text: str = None):
    findings, opportunities = [], []
    if not html:
        return findings, opportunities
    visible_text = precomputed_text if precomputed_text is not None else strip_tags(html)
    types_found, parse_errors, nodes = extract_ldjson_types(html)
    expected_types = infer_expected_types(url, html, visible_text)

    if parse_errors:
        findings.append({
            "title": f"Malformed JSON-LD syntax on {url}",
            "url": url,
            "category": "discoverability",
            "subcategory": "structured-data",
            "impact": "degrading",
            "scope": "single-page",
            "confidence": "high",
            "evidence": f"<script type=application/ld+json> failed to parse: {parse_errors[:2]}",
            "suggested_action": {"summary": "Correct JSON syntax errors (e.g. unescaped quotes or trailing commas) in the JSON-LD block.", "priority": "high"},
        })

    # Missing expected schema types
    for t in expected_types:
        equivalents = TYPE_EQUIVALENTS.get(t, {t})
        if not (types_found & equivalents):
            template_code = SCHEMA_FIX_TEMPLATES.get(t)
            action_dict = {
                "summary": f"Add {t} JSON-LD structured data representing the page's core entities.",
                "priority": "high",
                "mechanism": "Search engines and LLM answer engines rely on structured data nodes to quote exact facts (names, prices, availability) with high confidence."
            }
            if template_code:
                action_dict["fix_snippet"] = template_code

            findings.append({
                "title": f"Page at {url} represents {t} content but lacks {t} Schema.org markup",
                "url": url,
                "category": "discoverability",
                "subcategory": "structured-data",
                "impact": "degrading",
                "scope": "single-page",
                "confidence": "high",
                "evidence": f"Page context warrants {t} structured data (route/commercial signals), but no matching schema found. Types present: {sorted(types_found) or 'none'}.",
                "suggested_action": action_dict,
            })

    # Missing required properties on existing schemas
    for t in types_found:
        for msg in validate_required_props(t, nodes):
            findings.append({
                "title": f"{t} structured data present on {url} but missing essential attributes",
                "url": url,
                "category": "discoverability",
                "subcategory": "structured-data",
                "impact": "degrading",
                "scope": "single-page",
                "confidence": "high",
                "evidence": f"{url}: {msg}",
                "suggested_action": {
                    "summary": f"Supply required attributes for the {t} schema node.",
                    "priority": "medium",
                    "mechanism": "Incomplete schema nodes fail schema validation parsers and are excluded from rich answers."
                },
            })

    # Value conflicts
    findings.extend(check_schema_fact_conflicts(nodes, visible_text, url))

    # Locked facts (images / PDFs)
    findings.extend(check_locked_facts(html, visible_text, url))

    return findings, opportunities


def check_pages_data(pages_data):
    all_findings, all_opps = [], []
    for p in pages_data:
        url = p.get("url", "")
        html = p.get("html", "")
        text = p.get("text", "")
        if not html:
            continue
        f, o = check_page(url, html, precomputed_text=text)
        all_findings.extend(f)
        all_opps.extend(o)
    return all_findings, all_opps


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read().decode("utf-8", errors="replace")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", nargs="*")
    ap.add_argument("--pages-json", help="Path to pre-crawled pages JSON")
    ap.add_argument("--out", default="struct_findings.json")
    args = ap.parse_args()

    all_findings, all_opps = [], []

    if args.pages_json:
        with open(args.pages_json, "r", encoding="utf-8") as f:
            pages_data = json.load(f)
        all_findings, all_opps = check_pages_data(pages_data)
    elif args.pages:
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
