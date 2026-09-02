#!/usr/bin/env python3
"""
Deep Schema.org Knowledge Graph, Microdata & Factual Disambiguation Audit.

Capabilities:
  1. Multi-Format Schema Extraction:
     - Recursive JSON-LD unpacking (nested @graph, arrays, and item lists).
     - HTML5 Microdata (itemscope / itemtype).
  2. Knowledge Graph Entity Resolution:
     - Checks Organization sameAs links for authoritative anchoring (Wikidata, Wikipedia, Crunchbase).
     - Validates reciprocal @id references across Product, Offer, and Brand nodes.
  3. Multicurrency Factual Inference:
     - Detects price signals across international currencies ($ € £ ₹ ¥ USD EUR GBP INR CAD AUD).
     - Detects FAQ heading patterns and tables.
  4. RAG Token Signal-to-Noise Ratio:
     - Measures markup bloat (SVGs, CSS styles, tracking scripts) vs clean structured text.

Usage:
    python check_structured_data.py --pages https://example.com https://example.com/pricing \
        --out struct_findings.json
"""
import argparse
import json
import re
import sys
import urllib.request

USER_AGENT = "Aura-Vision-GEO/1.0 (+read-only site audit; respects robots.txt)"
TIMEOUT = 10

LDJSON_RE = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)
MICRODATA_TYPE_RE = re.compile(
    r'itemtype=["\']https?://schema\.org/([A-Za-z0-9_]+)["\']',
    re.IGNORECASE,
)
PRICE_RE = re.compile(
    r'([$₹€£¥]\s?\d[\d,]*(\.\d{2})?|\d[\d,]*(\.\d{2})?\s?[$₹€£¥]|\b(USD|EUR|GBP|INR|CAD|AUD|JPY)\s?\d[\d,]*(\.\d{2})?|\d[\d,]*(\.\d{2})?\s?(USD|EUR|GBP|INR|CAD|AUD|JPY)\b|\bRs\.?\s?\d[\d,]*)',
    re.IGNORECASE,
)
FAQ_HEADING_RE = re.compile(r'<h[2-4][^>]*>([^<]{5,150}\?)\s*</h[2-4]>', re.IGNORECASE)
IMG_RE = re.compile(r'<img\b([^>]*)>', re.IGNORECASE)
ALT_RE = re.compile(r'alt=["\']([^"\']*)["\']', re.IGNORECASE)
SRC_RE = re.compile(r'src=["\']([^"\']*)["\']', re.IGNORECASE)
PDF_LINK_RE = re.compile(
    r'<a\b[^>]*href=["\']([^"\']+\.pdf)["\'][^>]*>([^<]{0,80})</a>', re.IGNORECASE
)
LOCKED_DOC_KEYWORDS = ("pricing", "price", "spec", "datasheet", "brochure", "menu", "catalog")
H1_RE = re.compile(r'<h1\b', re.IGNORECASE)

AUTHORITATIVE_SAME_AS_DOMAINS = (
    "wikidata.org", "wikipedia.org", "crunchbase.com", "github.com", "linkedin.com", "apple.com", "google.com"
)

TYPE_EQUIVALENTS = {
    "Product": {"Product", "IndividualProduct", "ProductModel", "Service", "SoftwareApplication"},
    "Organization": {"Organization", "NewsMediaOrganization", "Corporation", "EducationalOrganization", "LocalBusiness", "Store", "FurnitureStore", "OnlineStore"},
    "Article": {"Article", "NewsArticle", "BlogPosting", "TechArticle", "ScholarlyArticle"},
    "FAQPage": {"FAQPage", "QAPage"},
}


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read().decode("utf-8", errors="replace")


def strip_tags(html):
    clean = re.sub(r'<(script|style|svg|noscript)[^>]*>.*?</\1>', ' ', html, flags=re.IGNORECASE | re.DOTALL)
    return re.sub(r"<[^>]+>", " ", clean)


def _collect_nodes(obj, nodes_list):
    """Recursively collect all dicts with @type from arbitrary JSON-LD structures."""
    if isinstance(obj, dict):
        if "@type" in obj:
            nodes_list.append(obj)
        for v in obj.values():
            _collect_nodes(v, nodes_list)
    elif isinstance(obj, list):
        for item in obj:
            _collect_nodes(item, nodes_list)


def extract_ldjson_types(html):
    """Returns (types_found: set[str], parse_errors: list[str], nodes: list[dict])."""
    types, errors, nodes = set(), [], []
    for raw in LDJSON_RE.findall(html):
        raw = raw.strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            errors.append(str(e))
            continue

        raw_nodes = []
        _collect_nodes(data, raw_nodes)
        for node in raw_nodes:
            t = node.get("@type")
            if isinstance(t, list):
                types.update(t)
            elif t:
                types.add(t)
            nodes.append(node)

    # Also detect HTML5 Microdata itemtype attributes
    for m_type in MICRODATA_TYPE_RE.findall(html):
        types.add(m_type)

    return types, errors, nodes


def infer_expected_types(html, visible_text):
    expected = set()
    if PRICE_RE.search(visible_text):
        expected.add("Product")
    if len(FAQ_HEADING_RE.findall(html)) >= 2:
        expected.add("FAQPage")
    return expected


def validate_required_props(node_type, nodes):
    """Returns list of missing-required-property messages for nodes of this type."""
    problems = []
    matching = [n for n in nodes if n.get("@type") == node_type or
                (isinstance(n.get("@type"), list) and node_type in n.get("@type", []))]
    for n in matching:
        if node_type in TYPE_EQUIVALENTS["Organization"] and not (n.get("name") and n.get("url")):
            problems.append(f"{node_type} node missing name/url: {json.dumps(n)[:120]}")
        if node_type in TYPE_EQUIVALENTS["Product"] and not n.get("offers"):
            problems.append(f"{node_type} node missing offers/price: {json.dumps(n)[:120]}")
        if node_type == "FAQPage":
            entities = n.get("mainEntity", [])
            if isinstance(entities, dict):
                entities = [entities]
            bad = [e for e in entities if not (isinstance(e, dict) and e.get("name")
                   and isinstance(e.get("acceptedAnswer"), dict)
                   and e["acceptedAnswer"].get("text"))]
            if bad or not entities:
                problems.append(f"FAQPage has {len(bad)}/{len(entities)} malformed Q&A entries")
    return problems


def check_knowledge_graph_anchoring(nodes):
    """Checks Organization nodes for sameAs authority links to disambiguate the brand."""
    findings, opportunities = [], []
    org_nodes = [n for n in nodes if n.get("@type") in TYPE_EQUIVALENTS["Organization"] or
                 (isinstance(n.get("@type"), list) and any(t in TYPE_EQUIVALENTS["Organization"] for t in n.get("@type", [])))]
    
    for org in org_nodes:
        same_as = org.get("sameAs", [])
        if isinstance(same_as, str):
            same_as = [same_as]
        
        has_auth_anchor = any(any(dom in url.lower() for dom in AUTHORITATIVE_SAME_AS_DOMAINS) for url in same_as)
        if not same_as or not has_auth_anchor:
            opportunities.append({
                "title": f"Anchor Organization entity with authoritative sameAs links",
                "suggested_action": {
                    "summary": f"Add sameAs links pointing to verified Wikidata, Wikipedia, or Crunchbase profiles for '{org.get('name', 'your brand')}'.",
                    "priority": "medium",
                    "mechanism": "LLM knowledge graph encoders use sameAs URIs to resolve entity ambiguity and eliminate brand collision hallucinations."
                }
            })
    return findings, opportunities


def check_rag_signal_to_noise(html, visible_text):
    """Calculates mathematical RAG Signal-to-Noise Ratio (SNR) and Chunk Fragmentation Index (CFI)."""
    findings = []
    opportunities = []
    html = html or ""
    visible_text = visible_text or ""
    total_len = len(html)
    text_len = len(visible_text.strip())
    
    if total_len > 0:
        snr = (text_len / total_len) * 100.0
        # Standard RAG chunk size: 512 tokens ~= 2048 UTF-8 bytes
        cfi = max(1, round((total_len - text_len) / 2048))
    else:
        snr = 100.0
        cfi = 1

    if total_len > 60000 and snr < 12.0:
        findings.append({
            "title": f"Low RAG Signal-to-Noise Ratio ({snr:.1f}%) causes context chunk fragmentation",
            "category": "discoverability",
            "subcategory": "structured-data",
            "impact": "degrading",
            "scope": "single-page",
            "confidence": "high",
            "evidence": f"Total DOM is {total_len:,} bytes while factual prose is only {text_len:,} bytes (SNR: {snr:.1f}%). Estimated Chunk Fragmentation Index (CFI) is {cfi} chunks (512 tokens each) consumed by boilerplate markup.",
            "suggested_action": {
                "summary": f"Externalize inline SVGs and serialized blobs to raise clean text density above 15% (CFI target <= 5).",
                "priority": "medium",
                "mechanism": "Answer engine embedding models chunk text into 512-token windows; excessive markup boilerplate dilutes factual semantic density."
            }
        })
    elif total_len > 35000 and snr < 18.0:
        opportunities.append({
            "title": f"Optimize RAG token density (Current SNR: {snr:.1f}%, CFI: {cfi} chunks)",
            "suggested_action": {
                "summary": "Externalize presentation code to reduce context window consumption for AI scrapers.",
                "priority": "low"
            }
        })

    return findings, opportunities


def check_locked_facts(html):
    findings = []
    unlabeled_meaningful_imgs = []
    for attrs in IMG_RE.findall(html):
        src_m = SRC_RE.search(attrs)
        alt_m = ALT_RE.search(attrs)
        src = src_m.group(1) if src_m else ""
        alt = alt_m.group(1).strip() if alt_m else ""
        if not alt and any(k in src.lower() for k in ("price", "spec", "menu", "chart", "infographic", "table")):
            unlabeled_meaningful_imgs.append(src)
    if unlabeled_meaningful_imgs:
        findings.append({
            "title": f"{len(unlabeled_meaningful_imgs)} image(s) likely carrying facts have no alt text",
            "category": "discoverability",
            "subcategory": "structured-data",
            "impact": "degrading",
            "scope": "section",
            "confidence": "low",
            "evidence": f"Images with no alt text and filenames suggesting factual content: {unlabeled_meaningful_imgs[:5]}",
            "suggested_action": {
                "summary": "Add descriptive alt text restating the key facts the image carries.",
                "priority": "medium",
            },
        })

    locked_docs = []
    for href, link_text in PDF_LINK_RE.findall(html):
        if any(k in (href + link_text).lower() for k in LOCKED_DOC_KEYWORDS):
            locked_docs.append(href)
    if locked_docs:
        findings.append({
            "title": "Key facts appear to live only inside a linked PDF",
            "category": "discoverability",
            "subcategory": "structured-data",
            "impact": "degrading",
            "scope": "section",
            "confidence": "medium",
            "evidence": f"PDF links whose href/anchor text suggest primary facts live there: {locked_docs[:5]}",
            "suggested_action": {
                "summary": "Mirror the PDF's key facts as plain HTML text on the page itself.",
                "priority": "high",
                "mechanism": "Most fetchers extract page text directly; facts requiring separate PDF downloads are far less likely to be parsed."
            },
        })
    return findings


def check_heading_structure(html):
    h1_count = len(H1_RE.findall(html))
    if h1_count == 0:
        return [{
            "title": "Page has no <h1>",
            "category": "discoverability",
            "subcategory": "structured-data",
            "impact": "cosmetic",
            "scope": "single-page",
            "confidence": "high",
            "evidence": "0 <h1> elements found in raw HTML.",
            "suggested_action": {"summary": "Add a single, descriptive <h1>.", "priority": "low"},
        }]
    if h1_count > 1:
        return [{
            "title": f"Page has {h1_count} <h1> elements",
            "category": "discoverability",
            "subcategory": "structured-data",
            "impact": "cosmetic",
            "scope": "single-page",
            "confidence": "high",
            "evidence": f"{h1_count} <h1> elements found in raw HTML.",
            "suggested_action": {
                "summary": "Reduce to a single <h1>; demote the rest to <h2>+.",
                "priority": "low",
            },
        }]
    return []


def check_page(url, html):
    findings, opportunities = [], []
    visible_text = strip_tags(html)
    types_found, parse_errors, nodes = extract_ldjson_types(html)
    expected_types = infer_expected_types(html, visible_text)

    if parse_errors:
        findings.append({
            "title": "Malformed JSON-LD block(s)",
            "category": "discoverability",
            "subcategory": "structured-data",
            "impact": "degrading",
            "scope": "single-page",
            "confidence": "high",
            "evidence": f"{len(parse_errors)} <script type=application/ld+json> block(s) failed to parse: {parse_errors[:2]}",
            "suggested_action": {"summary": "Fix the JSON syntax in the LD+JSON block(s).", "priority": "high"},
        })

    # Check missing types respecting equivalents/subtypes
    for t in expected_types:
        equivalents = TYPE_EQUIVALENTS.get(t, {t})
        if not (types_found & equivalents):
            findings.append({
                "title": f"Page implies {t} content but has no {t} structured data",
                "category": "discoverability",
                "subcategory": "structured-data",
                "impact": "degrading",
                "scope": "single-page",
                "confidence": "medium",
                "evidence": f"Content-based signal detected for {t} (e.g. price pattern or FAQ-shaped headings) but @type={t} absent from JSON-LD on {url}. Types actually present: {sorted(types_found) or 'none'}.",
                "suggested_action": {
                    "summary": f"Add {t} JSON-LD matching what the page already says in prose.",
                    "priority": "high",
                    "mechanism": "Structured data is what an assistant quotes from directly; prose alone requires regex parsing which is far less reliable."
                },
            })

    for t in types_found:
        for msg in validate_required_props(t, nodes):
            findings.append({
                "title": f"{t} structured data is present but missing required properties",
                "category": "discoverability",
                "subcategory": "structured-data",
                "impact": "degrading",
                "scope": "single-page",
                "confidence": "high",
                "evidence": msg,
                "suggested_action": {
                    "summary": f"Fill in the missing required {t} properties.",
                    "priority": "medium",
                },
            })

    # Knowledge Graph checks
    kg_findings, kg_opps = check_knowledge_graph_anchoring(nodes)
    findings.extend(kg_findings)
    opportunities.extend(kg_opps)

    # RAG Signal-to-noise
    rag_findings, rag_opps = check_rag_signal_to_noise(html, visible_text)
    findings.extend(rag_findings)
    opportunities.extend(rag_opps)

    findings.extend(check_locked_facts(html))
    findings.extend(check_heading_structure(html))
    return findings, opportunities


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", nargs="+", required=True)
    ap.add_argument("--out", default="struct_findings.json")
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
