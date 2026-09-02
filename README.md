# ai-visibility-audit

An Enterprise-Grade Agent Skill Marketplace built for the **Adobe University Hackathon 2026 (Round 3)**.

This system encodes automated technical reasoning to diagnose the two core failure modes of modern web properties:
1. **AI Invisibility & Misrepresentation (Off-Site Discoverability)**: Why a brand is blocked, skipped, or hallucinated by AI assistants (*ChatGPT, Claude, Perplexity, Gemini, Apple Intelligence*).
2. **The Engagement Drop-Off (On-Site Retention)**: Why human visitors who arrive from an AI citation bounce immediately without converting.

Built strictly per the **[agentskills.io](https://agentskills.io)** standard. Recommend-only, deterministic, read-only, and dependency-free (Python 3.8+ standard library).

---

## 1. Architectural Overview & Composition

The marketplace decomposes technical audit reasoning into **5 focused skills** coordinated by a designated entrypoint (`audit-orchestrator`).

```
                                  [ Input URL / Domain ]
                                             │
                                             ▼
                             ┌───────────────────────────────┐
                             │    audit-orchestrator (Root)  │
                             │  - Normalizes site URL        │
                             │  - Fetches shared page set    │
                             └───────────────┬───────────────┘
                                             │
         ┌───────────────────┬───────────────┴───────────────┬───────────────────┐
         ▼                   ▼                               ▼                   ▼
┌─────────────────┐ ┌─────────────────┐             ┌─────────────────┐ ┌─────────────────┐
│ crawl-and-      │ │ structured-     │             │ trust-and-      │ │ engagement-     │
│ render-audit    │ │ fact-audit      │             │ corroboration-  │ │ audit           │
│                 │ │                 │             │ audit           │ │                 │
│ • 12 AI Bots    │ │ • JSON-LD &     │             │ • Date Freshness│ │ • Broken Links  │
│ • robots.txt    │ │   Microdata     │             │ • Common-Noun   │ │ • Viewport Meta │
│ • Sitemaps      │ │ • Implied Price │             │   Disambiguation│ │ • Nav Semantics │
│ • DOM Hydration │ │ • Locked Facts  │             │ • Evergreen Age │ │ • Scannability  │
└────────┬────────┘ └────────┬────────┘             └────────┬────────┘ └────────┬────────┘
         │                   │                               │                   │
         └───────────────────┼───────────────────────────────┴───────────────────┘
                             ▼
             ┌───────────────────────────────┐
             │      aggregate_report.py      │
             │  • Jaccard Deduplication      │
             │  • Severity Derivation Matrix │
             │  • Sequential ID Assignment   │
             └───────────────┬───────────────┘
                             │
            ┌────────────────┴────────────────┐
            ▼                                 ▼
┌───────────────────────┐         ┌───────────────────────┐
│   audit_report.json   │         │    audit_report.md    │
│ (Machine-Readable)    │         │ (Executive Summary)   │
└───────────────────────┘         └───────────────────────┘
```

### Marketplace Manifest (`marketplace.json`)
```json
{
  "name": "ai-visibility-audit",
  "version": "1.0.0",
  "description": "Agent skill marketplace for AI-discoverability and on-site engagement diagnostics",
  "skills": [
    { "id": "audit-orchestrator", "path": "skills/audit-orchestrator", "entrypoint": true },
    { "id": "crawl-and-render-audit", "path": "skills/crawl-and-render-audit" },
    { "id": "structured-fact-audit", "path": "skills/structured-fact-audit" },
    { "id": "trust-and-corroboration-audit", "path": "skills/trust-and-corroboration-audit" },
    { "id": "engagement-audit", "path": "skills/engagement-audit" }
  ]
}
```

---

## 2. Skill Taxonomy & Failure Modes

### Skill 1: `audit-orchestrator` (Designated Entrypoint)
- **Role**: Coordinates the audit lifecycle. Resolves domain targets, executes a single-pass fetch of canonical routes, dispatches worker skills, deduplicates findings, and mechanically normalizes severity.
- **Mathematical Severity Derivation**: Evaluates raw worker findings across an immutable 3×3 `(Impact × Scope)` matrix:
  $$\text{Severity} = f(\text{Impact}, \text{Scope})$$

| Impact \ Scope | Sitewide | Section | Single-Page |
|---|---|---|---|
| **Blocking** | **Critical** (Blocks crawler or parsing entirely) | **High** | **High** |
| **Degrading** | **High** | **Medium** | **Medium** |
| **Cosmetic** | **Medium** | **Low** | **Low** |

- **Deduplication Engine**: Merges overlapping subcategory findings using Jaccard token similarity ($\ge 0.60$), keeping the most specific title and unioning the underlying evidence.

---

### Skill 2: `crawl-and-render-audit` (Discoverability Layers 1–2)
- **Problem**: Can an AI crawler enter the domain and read the content?
- **Checks Executed**:
  1. **Robots.txt AI Bot Matrix**: Evaluates permissions for 12 named AI user-agents: `GPTBot`, `OAI-SearchBot`, `ChatGPT-User`, `ClaudeBot`, `anthropic-ai`, `Claude-Web`, `PerplexityBot`, `Google-Extended`, `CCBot`, `Bytespider`, `Amazonbot`, `Applebot-Extended`.
  2. **Gzipped Sitemap Decompression**: Transparently parses standard XML and gzip-compressed `.xml.gz` sitemaps; evaluates `<lastmod>` timestamps against copyright years.
  3. **WAF-Guarded Indexability**: Constrains `noindex` detection to HTTP 200 responses to prevent Cloudflare/Akamai 403 challenge pages from causing false positives.
  4. **DOM Hydration Diff**: Measures raw HTTP text length against client-rendered SPA frameworks (`<div id="root">`, `<div id="app">`, empty bodies).

---

### Skill 3: `structured-fact-audit` (Discoverability Layer 3)
- **Problem**: Can an LLM extract specific, unambiguous facts (pricing, specs, FAQs)?
- **Checks Executed**:
  1. **Content-Inferred Schema Validation**: Infers required schema from visible text rather than URL paths:
     - Currency patterns (`$`, `₹`, `€`, `£`) $\implies$ requires `Product` / `Offer` schema.
     - Question clusters (`?`) $\implies$ requires `FAQPage` schema.
     - Brand/Company names $\implies$ requires `Organization` schema with `url` and `sameAs`.
  2. **Dual-Parser Engine**: Extracts JSON-LD (`application/ld+json`) with fallback to HTML5 Microdata (`itemtype="http://schema.org/..."`).
  3. **Locked-Fact Detection**: Flags critical pricing/specs trapped in alt-less images or PDF-only download links.
  4. **Heading Hierarchy**: Enforces single `<h1>` hierarchy to ensure clean RAG chunking.

---

### Skill 4: `trust-and-corroboration-audit` (Freshness & Identity)
- **Problem**: Does the assistant believe and trust the extracted facts?
- **Checks Executed**:
  1. **Common-Noun Entity Collision**: Evaluates brand disambiguation risks (e.g. *Linear* vs. linear equations, *Stripe* vs. physical stripes) and checks for authoritative `sameAs` Wikidata/Wikipedia anchoring.
  2. **Freshness & Staleness**: Compares visible timestamps and `Last-Modified` HTTP headers against temporal claims (*"in 2026"*, *"currently"*).
  3. **Single-Source Claim Fragility**: Flags bold unsupported claims that lack independent corroboration.

---

### Skill 5: `engagement-audit` (On-Site Visitor Retention)
- **Problem**: When a user clicks an AI citation, do they convert or immediately bounce?
- **Checks Executed**:
  1. **Dead-End Link Detection**: Samples internal links and verifies live HTTP status codes (flags `404 Not Found` and `403 Forbidden` routes).
  2. **Mobile Viewport Assurance**: Validates `<meta name="viewport" content="width=device-width, initial-scale=1">`.
  3. **Semantic Navigation**: Checks for primary `<nav>` wrapping (flags generic `<div>` headers on pricing/subpages).
  4. **GDPR Filtered Scannability**: Filters out top-of-body cookie consent dialogs to accurately measure above-the-fold value proposition clarity and average paragraph length.

---

## 3. Empirical Ground Truth Calibration

The marketplace heuristics were calibrated and validated against **10 real-world production domains**:

| Audited Domain | Key Technical Discoveries & Blindspots Uncovered | Marketplace Fix Applied |
|---|---|---|
| **Amazon India** (`amazon.in`) | Explicitly disallows all 9 AI bots in `robots.txt`; dead internal fallback directory returns HTTP 404. | Real live detection of `robots.txt` disallows + confirmed 404 endpoint tracking. |
| **The New York Times** (`nytimes.com`) | Allows `User-agent: *` but disallows all 9 AI bots; uses gzipped `.xml.gz` sitemaps. | Transparent `gzip.decompress()` sitemap stream parsing. |
| **Stripe** (`stripe.com`) | Emits **88 `<h1>` tags** on `/pricing` due to product card component headers; uses prose pricing with `FAQPage` schema but no `Product`/`Offer` schema. | Multi-`<h1>` detection and prose-to-schema inference. |
| **Linear** (`linear.app`) | Brand name collides with common math term; uses canvas SPA background and `/llms.txt`. | Entity disambiguation evaluation + `/llms.txt` detection. |
| **MDN Web Docs** (`developer.mozilla.org`) | Uses **0 JSON-LD blocks**, but publishes rich HTML5 Microdata (`itemtype="http://schema.org/TechArticle"`). | Dual JSON-LD + Microdata extraction parser. |
| **Basecamp** (`basecamp.com`) | Cookie consent banner placed at top of DOM body polluted above-the-fold orientation heuristics. | Automated cookie/consent container stripping before text analysis. |
| **Medium** (`medium.com`) | Returns HTTP 403 with a Cloudflare challenge page containing `<meta name="robots" content="noindex">`. | HTTP status code guard: `noindex` is only evaluated on HTTP 200 responses. |

---

## 4. Execution & Usage

### Method 1: Single-Command Pipeline Runner
Run a complete multi-skill audit from the command line:

```bash
# Audit any website (emits audit_report.json and audit_report.md)
python run_audit.py --site https://stripe.com --pages https://stripe.com https://stripe.com/pricing --out audit_report
```

### Method 2: Enterprise Web Dashboard
Launch the interactive web UI and live API server:

```bash
# Start the local dashboard server (Port 8000)
python server.py --port 8000
# Open http://127.0.0.1:8000 in your browser
```

**Dashboard Capabilities**:
- **0–100 AI Visibility Scorecard**: Dynamic circular SVG gauge with 5-pillar health bars.
- **AI Assistant Grounding Simulator**: Real-time status cards for ChatGPT, Claude, Perplexity, and Gemini.
- **Protocol Toolkit**: Instant, one-click `/llms.txt` builder and Schema.org JSON-LD generator for the audited domain.
- **Export Suite**: One-click download for machine-readable JSON and human-readable Markdown.

### Method 3: Running Worker Skills Independently
Each skill is self-contained and runnable independently:

```bash
# 1. Crawlability & robots.txt check
python skills/crawl-and-render-audit/scripts/check_crawlability.py --site https://stripe.com --pages https://stripe.com/pricing --out 1.json

# 2. Render gap analysis
python skills/crawl-and-render-audit/scripts/check_render_gap.py --pages https://stripe.com --out 2.json

# 3. Structured data & schema validation
python skills/structured-fact-audit/scripts/check_structured_data.py --pages https://stripe.com/pricing --out 3.json

# 4. Freshness & trust claims
python skills/trust-and-corroboration-audit/scripts/check_freshness.py --pages https://stripe.com --out 4.json

# 5. Engagement & dead links
python skills/engagement-audit/scripts/check_engagement.py --pages https://stripe.com --out 5.json

# 6. Aggregate into final deliverable
python skills/audit-orchestrator/scripts/aggregate_report.py --site https://stripe.com --inputs 1.json 2.json 3.json 4.json 5.json --out audit_report
```

---

## 5. Output Report Schema

Every audit produces a machine-readable JSON file (`audit_report.json`) adhering to the required schema:

```json
{
  "site": "https://stripe.com",
  "audited_at": "2026-09-02T13:40:15Z",
  "summary": {
    "total_findings": 2,
    "critical": 0,
    "high": 0,
    "medium": 1,
    "low": 1
  },
  "findings": [
    {
      "id": "F-001",
      "title": "Page implies Product content but has no Product structured data",
      "severity": "medium",
      "category": "discoverability",
      "confidence": "medium",
      "evidence": "Content-based signal detected for Product (price pattern '$0.30') but @type=Product absent from JSON-LD on https://stripe.com/pricing. Types actually present: FAQPage.",
      "suggested_action": {
        "summary": "Add Product/Offer JSON-LD matching what the page already says in prose.",
        "priority": "high",
        "mechanism": "Structured data is what an assistant quotes from directly; prose alone requires free-text parsing, which is far less reliable."
      }
    }
  ],
  "opportunities": [
    {
      "title": "Publish an llms.txt at the site root",
      "suggested_action": {
        "summary": "Add /llms.txt pointing AI agents at your canonical markdown entry point.",
        "priority": "low"
      }
    }
  ]
}
```

---

## 6. Hackathon Guardrails & Specification Compliance

- **agentskills.io Specification**: Every skill directory contains a valid `SKILL.md` declaring YAML frontmatter (`name`, `description`, `license`, `allowed-tools`), deterministic numbered procedures, and progressive disclosure (`references/` and `scripts/`).
- **Strictly Recommend-Only**: Zero live modifications, zero authenticated access, zero form submissions. All operations are non-destructive and read-only.
- **Lightweight & Portable**: Zero heavy dependencies or pre-trained neural network weights. Entire repository is **< 1 MB** (well below the 50 MB limit).
- **Execution Performance**: Full 5-skill pipeline completes in **~5 to 10 seconds** on standard hardware (well below the 5-minute limit).

---

## 7. Automated Testing & Verification Suite

This repository includes two automated test and sanity check scripts for judges and evaluators:

### 1. Generalization & Edge-Case Test Suite
Validates all 5 worker skills, recursive JSON-LD unrolling, multi-currency price detection, and schema compliance:
```bash
python test_generalization.py
```

### 2. Hackathon Compliance Validator
Verifies `marketplace.json` manifest structure, `agentskills.io` frontmatter conformity, package size budget, and safety guardrails:
```bash
python validate_submission.py
```
