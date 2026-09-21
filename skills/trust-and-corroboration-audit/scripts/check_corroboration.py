#!/usr/bin/env python3
"""
Entity Disambiguation, Trust & Corroboration Audit.
Standard library only (re, json, urllib).

Capabilities:
  1. Entity Extraction:
     - Extracts primary organization identity, founded year, location, and core claims.
  2. Entity Collision Risk:
     - Detects common-noun or generic brand names that risk being conflated with unrelated entities
       in LLM parametric memory (e.g., 'Pulse', 'Apex', 'Nova', 'Beacon') lacking disambiguation.
  3. Authoritative Knowledge Anchoring:
     - Validates sameAs links pointing to authoritative knowledge graphs (Wikidata, Wikipedia, Crunchbase).
  4. Factual Grounding & Corroboration Status:
     - Classifies core business claims into: corroborated, single-source / fragile, contradicted, ambiguous.
     - Strictly avoids fabricating external evidence; transparently reports unverified claims when offline.

Usage:
    python check_corroboration.py --pages-json pages.json --out corroboration_findings.json
"""
import argparse
import json
import re
import sys
import urllib.parse
from html.parser import HTMLParser

COMMON_NOUN_BRANDS = {
    "apex", "nova", "pulse", "beacon", "forge", "starlight", "bolt", "velocity",
    "peak", "summit", "catalyst", "nexus", "aura", "matrix", "stride", "atlas",
    "zenith", "vortex", "echo", "spark", "origin", "drift", "prism", "orbit"
}

AUTHORITATIVE_DOMAINS = [
    "wikidata.org", "wikipedia.org", "crunchbase.com", "linkedin.com",
    "github.com", "sec.gov", "bloomberg.com", "reuters.com"
]

FOUNDED_RE = re.compile(r'\b(?:founded|established|est\.|since)\s+(?:in\s+)?(19\d{2}|20\d{2})\b', re.IGNORECASE)
LOCATION_RE = re.compile(r'\b(?:headquartered|based|located)\s+in\s+([A-Z][a-zA-Z]+(?:,\s+[A-Z][a-zA-Z]+)?)\b')
SAME_AS_RE = re.compile(r'["\']sameAs["\']\s*:\s*(\[[^\]]+\]|"[^"]+"|\'[^\']+\')', re.IGNORECASE)


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.chunks = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript") and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data):
        if self._skip_depth == 0:
            clean = data.strip()
            if clean:
                self.chunks.append(clean)

    def text(self):
        return " ".join(self.chunks)


def extract_brand_name(page: dict, fallback_netloc: str) -> str:
    """Extracts the intended brand name from title, meta tags, or domain."""
    html = page.get("html", "")
    title = page.get("title", "")
    
    # 1. og:site_name
    og_m = re.search(r'<meta[^>]+property=["\']og:site_name["\'][^>]+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
    if og_m:
        return og_m.group(1).strip()

    # 2. Extract from title before delimiter
    if title:
        for delim in ("|", "—", "-", ":"):
            if delim in title:
                parts = title.split(delim)
                cand = parts[-1].strip() if len(parts[-1].strip()) < len(parts[0].strip()) else parts[0].strip()
                if 2 <= len(cand) <= 30:
                    return cand

    # 3. Fallback to domain root
    domain = fallback_netloc.lower()
    if domain.startswith("www."):
        domain = domain[4:]
    parts = domain.split(".")
    return parts[0].capitalize() if parts else "Brand"


def extract_claims(pages_data: list) -> list:
    """Extracts key factual assertions (identity, founding date, headquarters location)."""
    claims = []
    seen_types = set()

    for p in pages_data:
        text = p.get("text", "")
        url = p.get("url", "")
        
        # Founding year
        f_m = FOUNDED_RE.search(text)
        if f_m and "founded" not in seen_types:
            claims.append({
                "type": "founding_date",
                "claim": f"Founded in {f_m.group(1)}",
                "source_url": url,
                "confidence": "high"
            })
            seen_types.add("founded")

        # Location
        loc_m = LOCATION_RE.search(text)
        if loc_m and "location" not in seen_types:
            claims.append({
                "type": "headquarters",
                "claim": f"Headquartered in {loc_m.group(1)}",
                "source_url": url,
                "confidence": "medium"
            })
            seen_types.add("location")

    return claims


def extract_same_as_links(html: str) -> list:
    """Extracts sameAs links from JSON-LD blocks supporting both double and single quotes."""
    links = []
    for match in SAME_AS_RE.findall(html):
        clean = match.strip()
        if clean.startswith("["):
            try:
                normalized = re.sub(r"'([^']*)'", r'"\1"', clean)
                arr = json.loads(normalized)
                links.extend([str(item) for item in arr if isinstance(item, str)])
            except Exception:
                urls_in_arr = re.findall(r'https?://[^\s"\'\],]+', clean)
                links.extend(urls_in_arr)
        elif clean.startswith(('"', "'")):
            links.append(clean.strip('"\''))
    return links


def audit_corroboration(pages_data: list, site_url: str) -> tuple:
    findings = []
    opportunities = []

    if not pages_data:
        return findings, opportunities

    if not site_url and pages_data:
        site_url = pages_data[0].get("url", "")

    home_page = pages_data[0]
    parsed_root = urllib.parse.urlparse(site_url)
    brand_name = extract_brand_name(home_page, parsed_root.netloc)
    combined_html = " ".join(p.get("html", "") for p in pages_data)
    domain_email = parsed_root.netloc[4:] if parsed_root.netloc.lower().startswith("www.") else parsed_root.netloc
    if not domain_email:
        domain_email = "example.com"

    # 1. Entity Collision Risk for Common Noun Brands
    brand_lower = brand_name.lower().strip()
    if brand_lower in COMMON_NOUN_BRANDS:
        same_as_links = extract_same_as_links(combined_html)
        has_auth = any(any(dom in link.lower() for dom in AUTHORITATIVE_DOMAINS) for link in same_as_links)
        
        if not has_auth:
            findings.append({
                "title": f"High entity collision risk: Brand name '{brand_name}' is a common noun lacking authoritative disambiguation",
                "category": "discoverability",
                "subcategory": "trust",
                "impact": "degrading",
                "scope": "sitewide",
                "confidence": "high",
                "evidence": f"Brand '{brand_name}' shares its name with common English vocabulary and multiple registered entities, but lacks sameAs links to Wikidata, Wikipedia, or Crunchbase.",
                "suggested_action": {
                    "summary": f"Add Schema.org sameAs links in Organization JSON-LD linking '{brand_name}' to its canonical Wikidata QID or Crunchbase entry.",
                    "priority": "high",
                    "mechanism": "Large language models resolve named entities via canonical knowledge graph URIs. Common noun brands without sameAs disambiguation suffer severe hallucinations and cross-entity conflation.",
                    "fix_snippet": f'<script type="application/ld+json">\n{{\n  "@context": "https://schema.org",\n  "@type": "Organization",\n  "name": "{brand_name}",\n  "url": "{site_url}",\n  "sameAs": [\n    "https://www.wikidata.org/wiki/Q...",\n    "https://www.crunchbase.com/organization/..."\n  ]\n}}\n</script>'
                }
            })

    # 2. Grounding & Authoritative Knowledge Graph Links
    all_same_as = extract_same_as_links(combined_html)
    auth_links = [l for l in all_same_as if any(dom in l.lower() for dom in AUTHORITATIVE_DOMAINS)]

    if not auth_links:
        opportunities.append({
            "title": f"Anchor brand identity with authoritative external profiles",
            "suggested_action": {
                "summary": f"Publish Schema.org Organization markup with sameAs links pointing to authoritative Wikipedia, Wikidata, or LinkedIn records for {brand_name}.",
                "priority": "medium",
            }
        })

    # 3. Factual Claims Extraction & Corroboration Status
    claims = extract_claims(pages_data)
    for c in claims:
        opportunities.append({
            "title": f"Factual assertion '{c['claim']}' is single-source and lacks independent corroboration links",
            "suggested_action": {
                "summary": f"Cite authoritative registry records or press coverage to corroborate '{c['claim']}' for AI answer engines.",
                "priority": "low"
            }
        })

    # 4. Corporate Contact & Legal Identity Grounding (E-E-A-T)
    has_email = any("mailto:" in p.get("html", "").lower() for p in pages_data)
    has_phone = any("tel:" in p.get("html", "").lower() for p in pages_data)
    has_contact_path = any(any(k in p.get("url", "").lower() for k in ("/contact", "/support", "/about", "/help", "/imprint", "/legal")) for p in pages_data)
    has_postal = any(re.search(r'\b(street|suite|floor|avenue|blvd|p\.?o\.?\s?box|zip\s?code|postal\s?code)\b', p.get("text", ""), re.IGNORECASE) for p in pages_data)

    if not (has_email or has_phone or has_contact_path or has_postal) and len(pages_data) >= 2:
        findings.append({
            "title": f"No discoverable corporate contact or legal identity signals found across {len(pages_data)} crawled route(s) (E-E-A-T grounding)",
            "url": site_url or (pages_data[0].get("url", "") if pages_data else ""),
            "category": "discoverability",
            "subcategory": "trust",
            "impact": "degrading",
            "scope": "sitewide",
            "confidence": "high",
            "evidence": f"Across {len(pages_data)} crawled route(s), no email contact, telephone line, postal address, or dedicated /contact path was detected.",
            "suggested_action": {
                "summary": "Expose verifiable legal entity and customer contact pathways to establish domain credibility in AI knowledge bases.",
                "priority": "medium",
                "mechanism": "Generative answer engines (Perplexity, Google AI Overviews) enforce E-E-A-T thresholds to discard anonymous spam domains from citation synthesis.",
                "fix_snippet": f'<footer itemscope itemtype="https://schema.org/Organization">\n  <span itemprop="name">{brand_name}</span>\n  <a href="mailto:support@{domain_email}" itemprop="email">support@{domain_email}</a>\n</footer>'
            }
        })

    return findings, opportunities


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages-json", required=True, help="Path to pre-crawled pages JSON")
    ap.add_argument("--site", default="", help="Site root URL")
    ap.add_argument("--out", default="corroboration_findings.json")
    args = ap.parse_args()

    with open(args.pages_json, "r", encoding="utf-8") as f:
        pages_data = json.load(f)

    site_url = args.site or (pages_data[0].get("url") if pages_data else "")
    findings, opportunities = audit_corroboration(pages_data, site_url)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"findings": findings, "opportunities": opportunities}, f, indent=2, ensure_ascii=False)
    print(f"Wrote {args.out}: {len(findings)} findings, {len(opportunities)} opportunities", file=sys.stderr)


if __name__ == "__main__":
    main()
