#!/usr/bin/env python3
"""
Honest, Optional Empirical Search Grounding Check.
Standard library only (urllib.request, urllib.parse, json, os, sys, argparse, re).

Zero-Fabrication Guarantees:
  1. Real, falsifiable verification: tests whether external search backends return
     the site's own domain or brand entity for its identity query.
  2. Clean 'not_run' status: if no search capability (BRAVE_API_KEY, TAVILY_API_KEY,
     SERPAPI_API_KEY, or --empirical flag) is configured, it skips cleanly and reports
     'not_run'. Never fabricates results, scores, percentiles, or fake confidence numbers.
  3. Distinct labeling: findings are categorized under 'empirical_corroboration' / 'external_search',
     with evidence detailing the exact real query, provider, and actual results received.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request


def extract_search_target(site_url: str, pages_data: list | None = None) -> tuple[str, str]:
    """Extracts the normalized domain and inferred brand name."""
    if not site_url and pages_data:
        site_url = pages_data[0].get("url", "")
    parsed = urllib.parse.urlparse(site_url or "https://example.com")
    netloc = parsed.netloc.lower()
    if ":" in netloc:
        netloc = netloc.split(":")[0]
    domain = netloc[4:] if netloc.startswith("www.") else netloc

    brand = domain.split(".")[0].capitalize() if domain else "Brand"
    if pages_data:
        hp = pages_data[0]
        html = hp.get("html", "")
        title = hp.get("title", "")
        og_m = re.search(r'<meta[^>]+property=["\']og:site_name["\'][^>]+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
        if og_m:
            brand = og_m.group(1).strip()
        elif title:
            for delim in ("|", "—", "-", ":"):
                if delim in title:
                    parts = title.split(delim)
                    cand = parts[-1].strip() if len(parts[-1].strip()) < len(parts[0].strip()) else parts[0].strip()
                    if 2 <= len(cand) <= 30:
                        brand = cand
                        break

    return domain, brand


def query_external_search(
    domain: str,
    brand: str,
    enable_empirical: bool = False,
    api_key: str | None = None
) -> dict:
    """
    Executes a real external search query against configured providers.
    Supports Brave Search API, Tavily, SerpAPI, DuckDuckGo, and Wikipedia OpenSearch.
    If no capability is configured, cleanly returns status='not_run'.
    """
    brave_key = api_key or os.environ.get("BRAVE_API_KEY")
    tavily_key = api_key or os.environ.get("TAVILY_API_KEY")
    serpapi_key = api_key or os.environ.get("SERPAPI_API_KEY")
    is_enabled = enable_empirical or bool(os.environ.get("ENABLE_EMPIRICAL_CHECK")) or bool(brave_key or tavily_key or serpapi_key)

    query = domain or brand

    if not is_enabled:
        return {
            "status": "not_run",
            "reason": "Empirical search verification is optional and was not enabled. Provide --empirical or set an API key (BRAVE_API_KEY, TAVILY_API_KEY, SERPAPI_API_KEY) for live external validation.",
            "provider": None,
            "query": query,
            "domain_searched": domain,
            "matched": False,
            "matched_urls": [],
            "raw_results_count": 0,
            "evidence": None
        }

    # Provider 1: Brave Search API
    if brave_key:
        provider = "Brave Search API"
        url = f"https://api.search.brave.com/res/v1/web/search?q={urllib.parse.quote_plus(query)}&count=5"
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": brave_key,
            "User-Agent": "AuraVisionGEO-Audit/1.0"
        }
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="replace"))
            web_results = data.get("web", {}).get("results", [])
            returned_urls = [r.get("url", "") for r in web_results if r.get("url")]
            matched_urls = [u for u in returned_urls if domain and domain in u.lower()]
            matched = len(matched_urls) > 0
            evidence = (
                f"Queried {provider} with '{query}'. Provider returned {len(returned_urls)} result(s). "
                f"Target domain '{domain}' matched: {matched}."
                + (f" Matched URLs: {matched_urls[:3]}." if matched else f" Returned URLs: {returned_urls[:3]}.")
            )
            return {
                "status": "completed",
                "provider": provider,
                "query": query,
                "domain_searched": domain,
                "matched": matched,
                "matched_urls": matched_urls,
                "raw_results_count": len(returned_urls),
                "returned_urls_sample": returned_urls[:3],
                "evidence": evidence
            }
        except Exception as err:
            return {
                "status": "error",
                "provider": provider,
                "query": query,
                "domain_searched": domain,
                "matched": False,
                "matched_urls": [],
                "raw_results_count": 0,
                "reason": f"External search request to {provider} failed: {err}",
                "evidence": f"Request to {provider} failed ({err}). No empirical data could be verified."
            }

    # Provider 2: Tavily Search API
    elif tavily_key:
        provider = "Tavily Search API"
        url = "https://api.tavily.com/search"
        payload = json.dumps({"api_key": tavily_key, "query": query, "max_results": 5}).encode("utf-8")
        headers = {"Content-Type": "application/json", "User-Agent": "AuraVisionGEO-Audit/1.0"}
        try:
            req = urllib.request.Request(url, data=payload, headers=headers)
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="replace"))
            results = data.get("results", [])
            returned_urls = [r.get("url", "") for r in results if r.get("url")]
            matched_urls = [u for u in returned_urls if domain and domain in u.lower()]
            matched = len(matched_urls) > 0
            evidence = (
                f"Queried {provider} with '{query}'. Provider returned {len(returned_urls)} result(s). "
                f"Target domain '{domain}' matched: {matched}."
                + (f" Matched URLs: {matched_urls[:3]}." if matched else f" Returned URLs: {returned_urls[:3]}.")
            )
            return {
                "status": "completed",
                "provider": provider,
                "query": query,
                "domain_searched": domain,
                "matched": matched,
                "matched_urls": matched_urls,
                "raw_results_count": len(returned_urls),
                "returned_urls_sample": returned_urls[:3],
                "evidence": evidence
            }
        except Exception as err:
            return {
                "status": "error",
                "provider": provider,
                "query": query,
                "domain_searched": domain,
                "matched": False,
                "matched_urls": [],
                "raw_results_count": 0,
                "reason": f"External search request to {provider} failed: {err}",
                "evidence": f"Request to {provider} failed ({err}). No empirical data could be verified."
            }

    # Provider 3: SerpAPI
    elif serpapi_key:
        provider = "SerpAPI"
        url = f"https://serpapi.com/search?q={urllib.parse.quote_plus(query)}&api_key={serpapi_key}"
        headers = {"User-Agent": "AuraVisionGEO-Audit/1.0"}
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="replace"))
            results = data.get("organic_results", [])
            returned_urls = [r.get("link", "") for r in results if r.get("link")]
            matched_urls = [u for u in returned_urls if domain and domain in u.lower()]
            matched = len(matched_urls) > 0
            evidence = (
                f"Queried {provider} with '{query}'. Provider returned {len(returned_urls)} result(s). "
                f"Target domain '{domain}' matched: {matched}."
                + (f" Matched URLs: {matched_urls[:3]}." if matched else f" Returned URLs: {returned_urls[:3]}.")
            )
            return {
                "status": "completed",
                "provider": provider,
                "query": query,
                "domain_searched": domain,
                "matched": matched,
                "matched_urls": matched_urls,
                "raw_results_count": len(returned_urls),
                "returned_urls_sample": returned_urls[:3],
                "evidence": evidence
            }
        except Exception as err:
            return {
                "status": "error",
                "provider": provider,
                "query": query,
                "domain_searched": domain,
                "matched": False,
                "matched_urls": [],
                "raw_results_count": 0,
                "reason": f"External search request to {provider} failed: {err}",
                "evidence": f"Request to {provider} failed ({err}). No empirical data could be verified."
            }

    # Provider 4: DuckDuckGo Instant Answer API (Live Public Provider)
    else:
        provider = "DuckDuckGo Instant Answer API"
        url = f"https://api.duckduckgo.com/?q={urllib.parse.quote_plus(query)}&format=json"
        headers = {"User-Agent": "AuraVisionGEO-Audit/1.0"}
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="replace"))

            returned_urls = []
            if data.get("AbstractURL"):
                returned_urls.append(data["AbstractURL"])
            for r in data.get("Results", []):
                if isinstance(r, dict) and r.get("FirstURL"):
                    returned_urls.append(r["FirstURL"])
            for topic in data.get("RelatedTopics", []):
                if isinstance(topic, dict):
                    if topic.get("FirstURL"):
                        returned_urls.append(topic["FirstURL"])
                    for sub in topic.get("Topics", []):
                        if isinstance(sub, dict) and sub.get("FirstURL"):
                            returned_urls.append(sub["FirstURL"])

            matched_urls = [u for u in returned_urls if domain and domain in u.lower()]
            matched = len(matched_urls) > 0
            evidence = (
                f"Queried {provider} with '{query}'. Provider returned {len(returned_urls)} result(s). "
                f"Target domain '{domain}' matched: {matched}."
                + (f" Matched URLs: {matched_urls[:3]}." if matched else (f" Returned URLs: {returned_urls[:3]}." if returned_urls else " No results returned."))
            )
            return {
                "status": "completed",
                "provider": provider,
                "query": query,
                "domain_searched": domain,
                "matched": matched,
                "matched_urls": matched_urls,
                "raw_results_count": len(returned_urls),
                "returned_urls_sample": returned_urls[:3],
                "evidence": evidence
            }
        except Exception as ddg_err:
            # Fallback to Wikipedia OpenSearch Entity Corroboration API
            wiki_provider = "Wikipedia OpenSearch API"
            wiki_query = brand or domain
            wiki_url = f"https://en.wikipedia.org/w/api.php?action=opensearch&search={urllib.parse.quote_plus(wiki_query)}&limit=5&namespace=0&format=json"
            wiki_headers = {"User-Agent": "AuraVisionGEO-Audit/1.0"}
            try:
                w_req = urllib.request.Request(wiki_url, headers=wiki_headers)
                with urllib.request.urlopen(w_req, timeout=5) as w_resp:
                    w_data = json.loads(w_resp.read().decode("utf-8", errors="replace"))
                titles = w_data[1] if len(w_data) > 1 and isinstance(w_data[1], list) else []
                urls = w_data[3] if len(w_data) > 3 and isinstance(w_data[3], list) else []
                matched = any(brand.lower() in t.lower() for t in titles) if brand else False
                matched_urls = [u for u, t in zip(urls, titles) if brand and brand.lower() in t.lower()]
                evidence = (
                    f"Queried {wiki_provider} with '{wiki_query}' (after DuckDuckGo: {ddg_err}). "
                    f"Provider returned {len(titles)} entity result(s). Brand '{brand}' matched: {matched}."
                    + (f" Matched: {matched_urls[:2]}." if matched else f" Returned: {titles[:3]}.")
                )
                return {
                    "status": "completed",
                    "provider": wiki_provider,
                    "query": wiki_query,
                    "domain_searched": domain,
                    "matched": matched,
                    "matched_urls": matched_urls,
                    "raw_results_count": len(titles),
                    "returned_urls_sample": urls[:3],
                    "evidence": evidence
                }
            except Exception as wiki_err:
                return {
                    "status": "error",
                    "provider": f"{provider} / {wiki_provider}",
                    "query": query,
                    "domain_searched": domain,
                    "matched": False,
                    "matched_urls": [],
                    "raw_results_count": 0,
                    "reason": f"External search request failed: DDG ({ddg_err}), Wikipedia ({wiki_err})",
                    "evidence": f"Request to public search APIs failed (DDG: {ddg_err}, Wikipedia: {wiki_err}). No empirical data could be verified."
                }


def audit_empirical_search(
    pages_data: list,
    site_url: str,
    enable_empirical: bool = False,
    api_key: str | None = None
) -> tuple[dict, list, list]:
    """
    Executes optional empirical search grounding audit.
    Returns:
      (empirical_corroboration_dict, findings_list, opportunities_list)
    """
    findings = []
    opportunities = []

    domain, brand = extract_search_target(site_url, pages_data)
    result = query_external_search(domain, brand, enable_empirical=enable_empirical, api_key=api_key)

    if result.get("status") == "not_run":
        return result, findings, opportunities

    if result.get("status") == "error":
        return result, findings, opportunities

    if result.get("status") == "completed":
        if not result.get("matched"):
            # Domain was not returned for its own brand/domain query
            provider = result.get("provider", "")
            is_general_search = provider in ("Brave Search API", "Tavily Search API", "SerpAPI")
            confidence = "high" if is_general_search else "low"

            base_evidence = result.get("evidence", f"Queried search provider with '{domain}'. No matching URLs returned for target domain.")
            if not is_general_search:
                evidence = (
                    f"{base_evidence} (Note: Provider '{provider}' is an instant factual snippet/entity lookup rather than a general web search index. "
                    "Due to known coverage gaps for ordinary websites, this result should be treated as a weak signal rather than a confirmed discoverability problem.)"
                )
            else:
                evidence = base_evidence

            findings.append({
                "title": f"Empirical search check: Target domain '{domain}' not returned in external search results for query '{result.get('query')}'",
                "category": "empirical_corroboration",
                "subcategory": "external_search",
                "severity": "medium",
                "impact": "degrading",
                "scope": "section",
                "confidence": confidence,
                "evidence": evidence,
                "suggested_action": {
                    "summary": f"Establish external domain citations and brand search indexation for '{brand or domain}' so generative answer engines corroborate entity identity.",
                    "priority": "medium",
                    "mechanism": "Modern AI answer engines (ChatGPT, Perplexity, Google AI Overviews) corroborate entity claims via real-time web search retrieval. When a domain is absent from search results for its own identity query, retrieval pipelines lack confidence and omit citations."
                }
            })
        else:
            # Positive corroboration: record verified status without penalizing score
            opportunities.append({
                "title": f"Empirical brand presence verified: Domain '{domain}' confirmed in external search results for query '{result.get('query')}'",
                "suggested_action": {
                    "summary": f"Maintain authoritative citations and structured data to keep external search ranking aligned with AI retrieval pipelines.",
                    "priority": "low"
                }
            })

    return result, findings, opportunities


def main():
    parser = argparse.ArgumentParser(description="Empirical Search Grounding Audit (Honest & Optional)")
    parser.add_argument("--pages-json", default=None, help="Path to pre-crawled pages JSON")
    parser.add_argument("--site", default="", help="Site root URL")
    parser.add_argument("--empirical", action="store_true", help="Enable live empirical search verification")
    parser.add_argument("--api-key", default=None, help="Optional search provider API key")
    parser.add_argument("--out", default="empirical_findings.json", help="Output file path")
    args = parser.parse_args()

    pages_data = []
    if args.pages_json and os.path.exists(args.pages_json):
        with open(args.pages_json, "r", encoding="utf-8") as f:
            pages_data = json.load(f)

    site_url = args.site or (pages_data[0].get("url") if pages_data else "")
    meta, findings, opps = audit_empirical_search(
        pages_data,
        site_url,
        enable_empirical=args.empirical,
        api_key=args.api_key
    )

    out_payload = {
        "empirical_corroboration": meta,
        "findings": findings,
        "opportunities": opps
    }

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out_payload, f, indent=2, ensure_ascii=False)

    print(f"Wrote {args.out}: empirical status '{meta.get('status')}', {len(findings)} findings, {len(opps)} opportunities", file=sys.stderr)


if __name__ == "__main__":
    main()
