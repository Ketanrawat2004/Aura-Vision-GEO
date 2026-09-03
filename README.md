# AuraVision GEO

Generative Engine Optimization (GEO) & AI Discoverability Audit Marketplace built strictly in accordance with the **[agentskills.io](https://agentskills.io)** standard for the **Adobe University Hackathon 2026**.

AuraVision GEO diagnoses websites for generative answer-engine extraction barriers (off-site discoverability) and citation bounce friction (on-site visitor retention), emitting evidence-backed reports with prioritized, mechanism-sound fixes.

---

## 1. Marketplace Architecture & Composition

The repository implements 5 focused skills defined in `marketplace.json`, coordinated by a designated root entrypoint (`audit-orchestrator`):

| Skill ID | Directory | Role & Target Diagnostic Layer |
|---|---|---|
| **`audit-orchestrator`** *(Entrypoint)* | `skills/audit-orchestrator/` | Coordinates the audit lifecycle: performs single-pass HTTP fetching, distributes page sets to worker skills, merges findings via Jaccard similarity ($\ge 0.60$), and normalizes severities. |
| **`crawl-and-render-audit`** | `skills/crawl-and-render-audit/` | Audits `robots.txt` for 12 named AI crawlers (`GPTBot`, `ClaudeBot`, etc.), decompresses `.xml.gz` sitemaps, and detects SPA client-side hydration gaps. |
| **`structured-fact-audit`** | `skills/structured-fact-audit/` | Extracts Schema.org JSON-LD and HTML5 Microdata, infers required schemas from visible prose (pricing, FAQs, org), and flags locked facts. |
| **`trust-and-corroboration-audit`** | `skills/trust-and-corroboration-audit/` | Flags common-noun brand collisions, validates authoritative Wikidata/Wikipedia `sameAs` links, and checks temporal freshness. |
| **`engagement-audit`** | `skills/engagement-audit/` | Samples internal links for HTTP 404/403 dead ends, validates mobile viewport configuration, and inspects semantic navigation hierarchy. |

### How the Entrypoint Composes the Skills
1. **Single-Pass Fetch**: `audit-orchestrator` fetches the target domain's canonical routes concurrently into an in-memory page set. No target page is fetched more than once.
2. **Parallel Dispatch**: Passes the in-memory response data across all 4 worker skills.
3. **Deduplication & Normalization**: Runs `aggregate_report.py` to deduplicate overlapping findings using Jaccard token similarity ($\ge 0.60$) and derives final severities using an immutable 3×3 `(Impact × Scope)` matrix.
4. **Report Emission**: Generates `audit_report.json` (machine-readable) and `audit_report.md` (executive brief).

---

## 2. Quickstart & Headless Execution

### Option A: Headless Skill Entrypoint (Marketplace Standard)
```bash
# Direct entrypoint skill runner
python skills/audit-orchestrator/scripts/run_audit.py --site https://stripe.com --out audit_report

# Convenience root runner
python run_audit.py --site https://stripe.com --out audit_report
```
*Emits `audit_report.json` and `audit_report.md` in ~1.5 seconds.*

### Option B: Terminal CLI Auditor
```bash
python audit.py https://stripe.com
```
*Renders structured terminal diagnostics, category scores, and SHA-256 cryptographic audit proof.*

---

## 3. Verification & Test Suite

Verify standard compliance, package hygiene, and generalization across unseen sites:

```bash
# 1. Validate agentskills.io compliance, manifest, and package budget
python validate_submission.py

# 2. Run unit & generalization test suite (7 tests in ~0.12s)
python test_generalization.py
```

---

## 4. Output Report Specification

The platform emits machine-readable JSON matching `references/schema.md`:

```json
{
  "site": "https://stripe.com",
  "audited_at": "2026-09-02T13:40:15Z",
  "summary": { "total_findings": 2, "critical": 0, "high": 0, "medium": 1, "low": 1 },
  "findings": [
    {
      "id": "F-001",
      "title": "Page implies Product content but has no Product structured data",
      "severity": "medium",
      "category": "discoverability",
      "confidence": "medium",
      "evidence": "Content-based signal detected for Product (price pattern '$0.30') but @type=Product absent from JSON-LD on https://stripe.com/pricing.",
      "suggested_action": {
        "summary": "Add Product/Offer JSON-LD matching prose content.",
        "priority": "high",
        "mechanism": "Enables direct answer-engine extraction without free-text heuristic parsing."
      }
    }
  ],
  "opportunities": [
    {
      "title": "Publish an /llms.txt at the site root",
      "suggested_action": {
        "summary": "Add /llms.txt pointing AI agents at your canonical markdown entry point.",
        "priority": "low"
      }
    }
  ]
}
```

---

## 5. Severity Derivation Matrix

Worker skills propose `impact` (`blocking`, `degrading`, `cosmetic`) and `scope` (`sitewide`, `section`, `single-page`). The orchestrator deterministically derives the final `severity`:

| Impact \ Scope | Sitewide | Section | Single-Page |
|---|---|---|---|
| **Blocking** (Prevents extraction entirely) | **Critical** | **High** | **High** |
| **Degrading** (Degrades extraction accuracy) | **High** | **Medium** | **Medium** |
| **Cosmetic** (Styling or non-blocking defect) | **Medium** | **Low** | **Low** |

---

## 6. Engineering Hygiene & Rubric Alignment

- **Pure Python Standard Library**: Built with 0 external pip dependencies (`urllib`, `re`, `html.parser`, `hashlib`, `concurrent.futures`, `gzip`).
- **Read-Only Sandbox Guardrails**: Strictly non-destructive HTTP requests; zero target write operations, no credentials, no exploit vectors.
- **Package Size Budget**: Total package size is under 2.5 MB (well within the 50 MB limit).
- **Execution Performance**: Single-pass network architecture executes audits in under 2 seconds (limit is 5 minutes).
- **Generalization**: Content-inferred heuristics (multi-currency detection, question pattern analysis, brand entity disambiguation) operate robustly on unseen domains without domain hardcoding.

---

## 7. Repository Structure

```
.
├── marketplace.json                # agentskills.io marketplace manifest
├── run_audit.py                    # Root convenience invocation wrapper
├── audit.py                        # Terminal CLI diagnostic tool
├── validate_submission.py          # Automated compliance validator
├── test_generalization.py          # Unit & generalization test suite
├── examples/                       # Sample JSON and MD audit outputs
└── skills/
    ├── audit-orchestrator/         # Designated entrypoint skill
    ├── crawl-and-render-audit/     # Robots.txt, sitemaps, SPA hydration
    ├── structured-fact-audit/      # Schema.org JSON-LD and Microdata
    ├── trust-and-corroboration-audit/ # Entity disambiguation & freshness
    └── engagement-audit/           # 404 links, mobile viewport, navigation
```

---

## License

MIT License. Built for the Adobe University Hackathon 2026.
