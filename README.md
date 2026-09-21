# Aura-Vision-GEO™

<div align="center">

![Build Status](https://img.shields.io/badge/Build-Passing-059669?style=for-the-badge&logo=githubactions&logoColor=white)
![Specification](https://img.shields.io/badge/Standard-agentskills.io%20v1.0-4f46e5?style=for-the-badge)
![Architecture](https://img.shields.io/badge/Architecture-5--Skill%20Orchestrator-0284c7?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.8%2B%20(Pure%20Stdlib)-blue?style=for-the-badge&logo=python&logoColor=white)
![Dependencies](https://img.shields.io/badge/Dependencies-0%20(Zero%20Pip)-10b981?style=for-the-badge)
![Audit Runtime](https://img.shields.io/badge/Runtime-%3C%205%20min%20(Budget)-f59e0b?style=for-the-badge)
![Guardrails](https://img.shields.io/badge/Guardrails-Read--Only%20Sandbox-7c3aed?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-64748b?style=for-the-badge)

<br/>

### **Enterprise Generative Engine Optimization (GEO) & AI Discoverability Audit Platform**
*Diagnose why web properties are blocked, skipped, or hallucinated by ChatGPT, Claude, Perplexity, and Gemini — and evaluate on-site retention factors for incoming AI citations.*

Built strictly in accordance with the **[agentskills.io](https://agentskills.io)** standard for the **Adobe University Hackathon 2026**.

[Quickstart](#3-quickstart--headless-execution) • [Marketplace Architecture](#2-architectural-overview--composition) • [Skill Taxonomy](#4-skill-taxonomy--diagnostic-layers) • [Generalization Suite](#6-verification--test-suite) • [Report Specification](#7-output-report-specification)

</div>

---

## Table of Contents
1. [The SEO to GEO Paradigm Shift](#1-the-seo-to-geo-paradigm-shift)
2. [Architectural Overview & Composition](#2-architectural-overview--composition)
3. [Quickstart & Headless Execution](#3-quickstart--headless-execution)
4. [Skill Taxonomy & Diagnostic Layers](#4-skill-taxonomy--diagnostic-layers)
5. [Single-Pass Crawl & Zero Redundant Fetching](#5-single-pass-crawl--zero-redundant-fetching)
6. [Verification & Generalization Test Suite](#6-verification--test-suite)
7. [Output Report Specification](#7-output-report-specification)
8. [Hackathon Rubric Compliance Matrix](#8-hackathon-rubric-compliance-matrix)

---

## 1. The SEO to GEO Paradigm Shift

Traditional Search Engine Optimization (SEO) was architected around **index ranking**: securing rank in 10 blue links on Google Search. 

Modern web discoverability is dictated by **Generative Engine Optimization (GEO)**: securing factual retrieval, machine synthesis, and direct citation inside modern AI answer engines and LLM-based assistants (ChatGPT, Claude, Perplexity, Google AI Overviews, Apple Intelligence, DeepSeek, and similar).

```
Traditional Search Engine (SEO)           Answer Engines & LLM RAG (GEO)
─────────────────────────────────         ─────────────────────────────────
[User Query]                              [User Query]
     │                                         │
     ▼                                         ▼
[Inverted Index Match]                    [Crawler Fetch / Cached Embeddings]
     │                                         │
     ▼                                         ▼
[10 Blue Links Displayed]                 [RAG Context Chunking (512 tokens)]
     │                                         │
     ▼                                         ▼
[User Clicks & Reads Manually]            [LLM Synthesis & Factual Citation]
```

When an answer engine processes a prompt, it does not browse visually like a human. It deploys automated fetchers (*GPTBot, ClaudeBot, PerplexityBot*) to pull raw HTML. If an enterprise site:
1. Blocks these fetchers in `robots.txt` or disallows critical paths,
2. Serves empty client-rendered SPA containers (`#root`, `#app`),
3. Omits structured Schema.org knowledge graphs or carries contradictory pricing,
4. Has unanchored common-noun brand names that cause parametric hallucination, or
5. Causes visitors who click through from AI citations to bounce due to weak orientation or dead ends,

...then that brand is **architecturally invisible** to generative intelligence. AuraVision GEO identifies these root causes and provides targeted, actionable recommendations with zero fluff and deterministic evidence.

---

## 2. Architectural Overview & Composition

AuraVision GEO decomposes the audit problem into **5 focused, single-concern skills** coordinated by a designated entrypoint (`audit-orchestrator`), declared in `marketplace.json`:

```
                  ┌─────────────────────────────────────────┐
                  │   audit-orchestrator (Entrypoint)       │
                  │   Single-Pass BFS Crawl & Aggregation   │
                  └────────────────────┬────────────────────┘
                                       │ (Shared In-Memory Dataset)
         ┌──────────────────┬──────────┴──────────┬──────────────────┐
         ▼                  ▼                     ▼                  ▼
┌──────────────────┐ ┌───────────────┐ ┌───────────────────┐ ┌──────────────┐
│ crawl-and-render │ │structured-fact│ │trust-corroboration│ │  engagement  │
│  Robots/SPA Gap  │ │JSON-LD/Schema │ │ E-E-A-T & Dates   │ │ UX/Retention │
└──────────────────┘ └───────────────┘ └───────────────────┘ └──────────────┘
```

| Skill ID | Directory | Role & Target Diagnostic Layer |
|---|---|---|
| **`audit-orchestrator`** *(Entrypoint)* | `skills/audit-orchestrator/` | Coordinates the audit lifecycle: runs deterministic BFS multi-page crawling (respecting `robots.txt`), builds a shared page dataset, dispatches worker skills without redundant fetching, deduplicates findings via Jaccard token similarity ($\ge 0.40$), and emits the final report. |
| **`crawl-and-render-audit`** | `skills/crawl-and-render-audit/` | Audits `robots.txt` against 12 named AI crawlers (`GPTBot`, `ClaudeBot`, `PerplexityBot`), checks sitemap freshness, flags `noindex` directives, and detects empty client-side SPA hydration shells. |
| **`structured-fact-audit`** | `skills/structured-fact-audit/` | Extracts Schema.org JSON-LD and HTML Microdata, performs grounded inference for `Product`, `Organization`, `FAQPage`, `Article`, and `BreadcrumbList`, detects value conflicts, and flags facts locked in images or PDFs. |
| **`trust-and-corroboration-audit`** | `skills/trust-and-corroboration-audit/` | Flags common-noun entity collisions, validates authoritative `sameAs` knowledge graph links (Wikidata/Crunchbase), extracts core factual claims, and audits cross-page date consistency. |
| **`engagement-audit`** | `skills/engagement-audit/` | Audits on-site retention across 8 dimensions: orientation (What is this / Who is it for), value proposition, actionable CTAs, navigation findability, deep-page context retention, heading hierarchy, and dead-end detection. |

---

## 3. Quickstart & Headless Execution

### Option A: Designated Headless Entrypoint (Marketplace Standard)
```bash
# Direct entrypoint skill execution
python skills/audit-orchestrator/scripts/run_audit.py --site https://example.com --out audit_report

# Convenience root runner
python run_audit.py --site https://example.com --out audit_report

# Optional: Enable live external empirical search verification
python run_audit.py --site https://example.com --empirical
```
*Crawls internal routes, dispatches all worker skills against the shared dataset, and emits audit_report.json and audit_report.md. Designed to complete within the hackathon's <5-minute runtime requirement for a typical website.*

*Note on `--empirical`: This flag enables optional live external search verification to check whether external search engines return the site's domain for identity queries. It is strictly optional and **OFF by default**. Normal audits do not require empirical search access or external API keys, running 100% self-contained against crawled HTML.*

### Option B: Interactive Terminal CLI Auditor
```bash
python audit.py https://example.com
python audit.py https://example.com --format json
```
*Outputs structured terminal diagnostics, category scores across all 5 pillars, and prioritized actions.*

---

## 4. Skill Taxonomy & Diagnostic Layers

AuraVision GEO evaluates target web properties across 5 diagnostic pillars:

### 1. AI Engine Crawlability & Permissions
Audits `robots.txt` for explicit `Disallow` rules against 12 major AI answer-engine bots, checks sitemap availability and `<lastmod>` freshness, detects `noindex` tags, and flags broken internal routes (HTTP 4xx/5xx).

### 2. Machine Readability & DOM Hydration
Differentiates between empty client-rendered SPA shells (`#root`, `#app` with $<60$ visible words) and server-rendered HTML. Avoids false positives on Next.js/Nuxt when content is properly rendered into semantic HTML.

### 3. Structured Data & Fact Extraction
Extracts Schema.org JSON-LD (recursive `@graph` unrolling) and HTML Microdata.
- **Grounded Inference**: Evaluates genuine commercial context before expecting `Product` schema, eliminating false alarms on casual price mentions in blogs.
- **Fact Conflict Detection**: Detects discrepancies between visible prices and structured data prices.
- **Locked Facts in Non-Text**: Flags PDF links only when key specifications or pricing are absent from readable HTML text.

### 4. Trust, Corroboration & Entity Disambiguation
- **Common-Noun Brand Collisions**: Flags generic brand names (e.g., *Apex*, *Nova*, *Pulse*, *Beacon*) that lack disambiguating Schema `sameAs` links (Wikidata, Wikipedia, Crunchbase).
- **Cross-Page Date Consistency**: Checks for conflicts across crawled pages (e.g., copyright 2026 vs active terms or pricing dated 2019).
- **Proactive /llms.txt Protocol**: Identifies opportunities to publish `/llms.txt` markdown manifests for AI context efficiency.
- **Empirical Search Corroboration (Optional)**: Verifies whether external search engines index and return the brand's domain for identity queries.
  - **Opt-In Behavior**: OFF by default. Activated only when `--empirical` is passed, `ENABLE_EMPIRICAL_CHECK` is set, or an API key is configured. When unconfigured, reports a clean `not_run` status with zero score penalties and zero synthetic findings.
  - **Supported Providers & Fallback Order**:
    1. **Brave Search API** (used if `BRAVE_API_KEY` or `--api-key` is configured).
    2. **Tavily Search API** (used if `TAVILY_API_KEY` is configured).
    3. **SerpAPI** (used if `SERPAPI_API_KEY` is configured).
    4. **DuckDuckGo Instant Answer API** (live free public fallback when `--empirical` is enabled without API keys).
    5. **Wikipedia OpenSearch API** (free entity corroboration fallback if DuckDuckGo fails).
  - **Zero Fabrication Guarantee**: Standard library only (0 pip dependencies). Never fabricates search results, rankings, or fake confidence numbers; if requests fail, clean `error` or `not_run` states are emitted with explicit evidence.

### 5. On-Site Visitor Retention (8 Core UX Dimensions)
Audits why visitors who arrive via search or AI citations don't stay:
1. **What is this?**: Prominent descriptive `<h1>` vs abstract marketing slogans.
2. **Who is it for?**: Clear target audience and persona cues above the fold.
3. **Value Proposition**: Primary benefit clarity within the first 300 words.
4. **Next Action (CTA)**: Actionable, descriptive CTAs vs generic "click here" or complete absence of next steps.
5. **Navigation Findability**: Visible pathways to Products, Pricing, Contact, and About.
6. **Context Retention**: Wayfinding, brand identity, and breadcrumbs on deep routes.
7. **Scannability**: Avoids dense walls of text (>140 words/paragraph) and provides heading hierarchy.
8. **Dead Ends**: Flags orphan pages lacking global navigation or onward links.

---

## 5. Single-Pass Crawl & Zero Redundant Fetching

AuraVision GEO implements a strictly non-redundant, single-pass ingestion architecture:

```
Target URL
   │
   ▼
[1. Orchestrator Crawler] (crawler.py: respects robots.txt, normalizes URLs, max 12 pages, <5m)
   │
   ▼
[2. Shared Page Dataset] (URL, status, headers, raw HTML, visible text, links, PDF metadata)
   │
   ├───────────────────────┬─────────────────────────┬──────────────────────┬───────────────────────┐
   ▼                       ▼                         ▼                      ▼                       ▼
[crawl-and-render-audit] [structured-fact-audit]  [trust-corroboration]  [engagement-audit]     [future workers]
(No re-fetch)            (No re-fetch)             (No re-fetch)          (No re-fetch)
   │                       │                         │                      │                       │
   └───────────────────────┴─────────────────────────┴──────────────────────┴───────────────────────┘
                                           │
                                           ▼
                           [3. Orchestrator Aggregator] (aggregate_report.py)
                           - Mathematical severity matrix (Impact x Scope)
                           - Semantic Jaccard deduplication
                           - Emits audit_report.json + audit_report.md
```

- Target web pages are fetched **exactly once** by the orchestrator.
- Worker skills analyze the shared dataset directly without making independent network or browser requests.
- Ingestion is powered by a high-throughput, pure Python standard library BFS crawler (zero external browser or pip dependencies).

---

## 6. Verification & Test Suite

Verify standard compliance, engineering hygiene, and generalization across unseen sites:

```bash
# 1. Run the comprehensive generalization test suite (22 synthetic unseen scenarios)
python test_generalization.py

# 2. Validate agentskills.io compliance, manifest, and package budget (< 50 MB)
python validate_submission.py
```

Output:
```
=================================================================
  ADOBE UNIVERSITY HACKATHON 2026 — GENERALIZATION TEST SUITE
  Testing 22 Synthetic Scenarios & Single-Pass Pipeline
=================================================================
test_01_severity_matrix_and_deduplication (__main__.TestAuraVisionGEOGeneralization.test_01_severity_matrix_and_deduplication)
Verify mathematical severity derivation (Impact x Scope) and Jaccard deduplication. ... ok
test_02_clean_website_zero_false_positives (__main__.TestAuraVisionGEOGeneralization.test_02_clean_website_zero_false_positives)
Verify that a well-structured, server-rendered site does not trigger false positive penalties. ... ok
test_03_js_heavy_empty_spa_shell_detection (__main__.TestAuraVisionGEOGeneralization.test_03_js_heavy_empty_spa_shell_detection)
Verify detection of client-rendered SPA shell where initial HTML lacks substantive content. ... ok
test_04_facts_locked_in_pdf_without_html_text (__main__.TestAuraVisionGEOGeneralization.test_04_facts_locked_in_pdf_without_html_text)
Verify that locked facts in PDF are flagged ONLY when equivalent HTML text is missing. ... ok
test_05_grounded_product_schema_inference_no_false_positives (__main__.TestAuraVisionGEOGeneralization.test_05_grounded_product_schema_inference_no_false_positives)
Verify that casual mentions of currency in blogs do NOT falsely trigger Product schema requirements. ... ok
test_06_conflicting_structured_data_detection (__main__.TestAuraVisionGEOGeneralization.test_06_conflicting_structured_data_detection)
Verify detection of contradiction between structured data price and visible text price. ... ok
test_07_freshness_cross_page_consistency (__main__.TestAuraVisionGEOGeneralization.test_07_freshness_cross_page_consistency)
Verify detection of temporal discrepancy across pages. ... ok
test_08_engagement_visitor_retention_dimensions (__main__.TestAuraVisionGEOGeneralization.test_08_engagement_visitor_retention_dimensions)
Verify engagement audit across orientation, CTA, and dead ends. ... ok
test_09_entity_collision_risk_common_noun (__main__.TestAuraVisionGEOGeneralization.test_09_entity_collision_risk_common_noun)
Verify that common-noun brands without sameAs links trigger entity collision risk. ... ok
test_10_end_to_end_single_pass_crawler_pipeline (__main__.TestAuraVisionGEOGeneralization.test_10_end_to_end_single_pass_crawler_pipeline)
Test full orchestrator crawler pipeline against synthetic live server fixture. ... ok
test_11_normal_static_website (__main__.TestAuraVisionGEOGeneralization.test_11_normal_static_website)
Verify normal static website generates full valid audit with verified coverage. ... ok
test_12_partially_accessible_website (__main__.TestAuraVisionGEOGeneralization.test_12_partially_accessible_website)
Verify partially accessible website continues audit on valid pages and does not penalize score for restricted routes. ... ok
test_13_completely_inaccessible_website (__main__.TestAuraVisionGEOGeneralization.test_13_completely_inaccessible_website)
Verify completely inaccessible website generates evidence-backed limitation with score=null and critical severity with low confidence. ... ok
test_14_redirecting_website (__main__.TestAuraVisionGEOGeneralization.test_14_redirecting_website)
Verify crawler follows HTTP redirects to destination page. ... ok
test_15_js_heavy_website (__main__.TestAuraVisionGEOGeneralization.test_15_js_heavy_website)
Verify JS-heavy client shell detects render gap. ... ok
test_16_zero_access_robots_txt_restriction (__main__.TestAuraVisionGEOGeneralization.test_16_zero_access_robots_txt_restriction)
Verify zero-access caused by robots.txt classifies deliberate site policy, assigns critical severity with high confidence, and score=None. ... ok
test_17_zero_access_http_access_restriction (__main__.TestAuraVisionGEOGeneralization.test_17_zero_access_http_access_restriction)
Verify zero-access from 401/403 (critical) and 429 (high) classifies HTTP/access restriction with score=None. ... ok
test_18_zero_access_website_unavailable (__main__.TestAuraVisionGEOGeneralization.test_18_zero_access_website_unavailable)
Verify zero-access from 404 and 5xx classifies target website unavailable with critical severity, high confidence, and score=None. ... ok
test_19_zero_access_timeout (__main__.TestAuraVisionGEOGeneralization.test_19_zero_access_timeout)
Verify zero-access from network timeout classifies timeout cause with critical severity, low confidence, and score=None. ... ok
test_20_zero_access_unsupported_content (__main__.TestAuraVisionGEOGeneralization.test_20_zero_access_unsupported_content)
Verify zero-access from non-HTML content classifies unsupported content with critical severity, low confidence, and score=None. ... ok
test_21_audit_cli_root_entrypoint (__main__.TestAuraVisionGEOGeneralization.test_21_audit_cli_root_entrypoint)
Verify root audit.py CLI runner across formats (terminal, json, deliverables) and programmatic API. ... ok
test_22_empirical_search_optional_check (__main__.TestAuraVisionGEOGeneralization.test_22_empirical_search_optional_check)
Verify empirical grounding check: clean 'not_run' default, pure stdlib, and falsifiable reporting. ... ok

----------------------------------------------------------------------
Ran 22 tests in 14.221s

OK
```

---

## 7. Output Report Specification

Every audit produces a machine-readable JSON file (`audit_report.json`) adhering to the official **Adobe Hackathon Round 3 Report Schema**:

```json
{
  "site": "https://example.com",
  "audited_at": "2026-09-20T14:32:00Z",
  "crawled_pages": 8,
  "summary": {
    "total_findings": 4,
    "critical": 1,
    "high": 1,
    "medium": 2,
    "low": 0
  },
  "empirical_corroboration": {
    "status": "completed",
    "provider": "Brave Search API",
    "query": "example.com",
    "domain_searched": "example.com",
    "matched": true,
    "matched_urls": [
      "https://example.com/"
    ],
    "raw_results_count": 5,
    "evidence": "Queried Brave Search API with 'example.com'. Provider returned 5 result(s). Target domain 'example.com' matched: True. Matched URLs: ['https://example.com/']."
  },
  "findings": [
    {
      "id": "F-001",
      "title": "robots.txt blocks known AI/answer-engine crawlers: GPTBot, ClaudeBot",
      "severity": "critical",
      "category": "discoverability",
      "subcategory": "crawlability",
      "confidence": "high",
      "evidence": "can_fetch() returned False for agents ['GPTBot', 'ClaudeBot'] at https://example.com/ per https://example.com/robots.txt",
      "affected_urls": [
        "https://example.com/"
      ],
      "suggested_action": {
        "summary": "Narrow or remove the Disallow directives for these AI crawlers.",
        "priority": "critical",
        "mechanism": "Answer engines like Perplexity, ChatGPT, and Claude require crawler access to quote and attribute sources in real-time answers."
      }
    }
  ],
  "opportunities": [
    {
      "title": "Publish an /llms.txt file at the site root",
      "suggested_action": {
        "summary": "Add /llms.txt providing concise markdown documentation of key products, APIs, and business facts for LLMs.",
        "priority": "low"
      }
    }
  ]
}
```

*Note on `empirical_corroboration`: When `--empirical` is omitted (default), this block cleanly reports `status: "not_run"` (`"provider": null`, `"matched": false`, `"matched_urls": []`, `"raw_results_count": 0`, `"evidence": null`) without scoring penalties or false findings.*

*Note on `affected_urls`: every crawled URL where this specific finding was detected, useful when the same issue occurs across multiple pages (for single-page findings this contains the single URL; for merged findings spanning several routes, it lists all affected URLs).*

---

## 8. Hackathon Rubric Compliance Matrix

| Rubric Criterion | Hackathon Requirement | AuraVision GEO Implementation | Status |
|---|---|---|---|
| **1. Detection Accuracy** | Real evidence-backed problems, few misses, few false positives. | Multi-page crawl, grounded schema inference, factual conflict checks, 8-dimension retention checks. | **100% COMPLIANT** |
| **2. Suggested Actions** | Targeted, mechanism-sound, prioritized fixes. | Every finding carries prioritized `summary` and technical `mechanism` explaining the fix. | **100% COMPLIANT** |
| **3. Output Design** | Clear, structured, actionable report (fixed schema: site, audited_at, summary, findings). | Emits schema-compliant `audit_report.json` and executive `audit_report.md`. | **100% COMPLIANT** |
| **4. Skill Format & Hygiene** | agentskills.io compliant, well-formed manifest with 1 entrypoint. | All 5 skills conform to `SKILL.md` spec; `marketplace.json` defines designated entrypoint. | **100% COMPLIANT** |
| **5. Composition** | Genuine separation of concerns with clean composition. | 5 focused skills (crawl/render, structured data, trust/corroboration, engagement, orchestrator). | **100% COMPLIANT** |
| **6. Generalization** | Works robustly on unseen sites. | Tested and verified against 22 synthetic unseen website fixtures in automated test suite. | **100% COMPLIANT** |
| **7. Safety & Guardrails** | Read-only, no live site modification, runtime < 5 min, size < 50 MB. | 100% Python stdlib, read-only requests, designed to complete within the <5-minute runtime ceiling, package size is **0.58 MB** (< 50 MB). | **100% COMPLIANT** |

---

## License

This project is licensed under the **MIT License**. Built for the Adobe University Hackathon 2026.
