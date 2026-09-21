---
name: trust-and-corroboration-audit
description: Checks whether a brand's identity is disambiguated from unrelated entities, evaluates common-noun collision risks, verifies authoritative knowledge graph anchors (Wikidata/Crunchbase sameAs), extracts core factual claims, and audits cross-page date consistency and temporal freshness.
license: MIT
allowed-tools: [bash, http_fetch, web_search]
---

# Trust, Corroboration & Entity-Disambiguation Audit

## When to use
Called by `audit-orchestrator`. Covers Appendix D ("machines tend to treat a fact as more trustworthy when many independent places say the same thing... a related problem is mistaken identity") and the freshness half of Appendix C.

## Inputs
- Shared page set from orchestrator (headers, HTML, text, metadata).
- `site` root URL.

## Procedure (deterministic)

1. **Entity Collision Risk & Disambiguation** (`scripts/check_corroboration.py`):
   - Extract brand name from `og:site_name`, `<title>`, or domain.
   - Detect if brand name is a common noun (e.g. Apex, Nova, Pulse, Beacon, Forge) prone to parametric entity confusion in LLMs.
   - If common-noun brand lacks authoritative `sameAs` links (Wikidata, Wikipedia, Crunchbase), flag as high-risk entity collision defect.

2. **Authoritative Knowledge Graph Anchoring**:
   - Check presence of `sameAs` links on `Organization` schema to authoritative databases (Wikidata, Wikipedia, Crunchbase, official GitHub/LinkedIn).

3. **Factual Claim Grounding & Corroboration Status**:
   - Extract primary claims: founding date, headquarters location, and core capabilities.
   - Classify claims into: `corroborated`, `single-source / fragile`, `contradicted`, or `ambiguous`.
   - In offline or sandbox environments, transparently report claims as unverified / single-source without fabricating external citations.

4. **Evidence-Based Freshness & Cross-Page Consistency** (`scripts/check_freshness.py`):
   - Compare explicit timestamps: HTTP `Last-Modified` headers, `article:modified_time` meta tags, `<time>` tags, and textual dates.
   - Cross-page date conflict detection: detect conflicting copyright years or active terms/pricing dated >3 years old on modern sites.
   - Never flag content as stale purely because a date is absent.

5. **Honest Empirical Search Grounding (Optional)** (`scripts/check_empirical_search.py`):
   - Validates brand/domain external discoverability via live search backends (Brave, Tavily, SerpAPI, DuckDuckGo).
   - Skips cleanly with `not_run` status when unconfigured, avoiding any fabricated data or false penalties.
   - Labels empirical findings under `empirical_corroboration` with exact query and real response evidence.

## Output
`{"findings": [...], "opportunities": [...], "empirical_corroboration": {...}}` conforming to the shared schema.
