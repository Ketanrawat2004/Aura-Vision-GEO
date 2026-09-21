---
name: structured-fact-audit
description: Checks whether the facts on a readable page are actually extractable by a machine — Schema.org JSON-LD and Microdata validity, grounded inference for Product, Organization, FAQPage, Article, and BreadcrumbList schemas, factual consistency between visible text and markup, and detection of facts locked in non-text carriers (uncaptioned images or PDFs) where HTML equivalent is absent.
license: MIT
allowed-tools: [bash, http_fetch]
---

# Structured & Extractable Facts Audit

## When to use
Called by `audit-orchestrator`. Covers Appendix A layer 3 and Appendix C ("the more explicitly and unambiguously a fact is stated in plain, readable text, the more likely a machine extracts it correctly; the more it's implied, buried, or locked inside something non-textual, the more likely it's missed").

## Inputs
- Shared page set from the orchestrator (URL, status, headers, raw HTML, visible text).

## Procedure (deterministic)

1. **Extract every JSON-LD block and Microdata node** (`scripts/check_structured_data.py`):
   - Recursively unpack nested `@graph`, arrays, and item lists.
   - Collect the set of `@type` values present per page and validate JSON syntax.

2. **Grounded Schema Inference (False-Positive Elimination)**:
   - Rather than assuming every mention of currency requires `Product` schema, evaluate page intent:
     - Commercial offering (`/pricing`, `/products`, repeated tier tables, e-commerce cart/buy signals) → expect `Product`/`Offer`.
     - 2+ Q&A headings with question marks on FAQ/help routes → expect `FAQPage`.
     - Homepage and root brand routes → expect `Organization` and `WebSite`.
     - In-depth editorial content (`/blog/`, `/news/`, `/article/`) → expect `Article`/`BlogPosting`.
     - Deep subpages (2+ path segments) → expect `BreadcrumbList`.

3. **Validate Required Properties**:
   - `Organization` → requires `name` and `url`.
   - `Product` → requires `name` and `offers` (with price specification).
   - `FAQPage` → requires `mainEntity` with valid `Question` and `acceptedAnswer.text`.

4. **Factual Consistency & Conflict Detection**:
   - Compare structured data values (e.g. `Offer.price`) against visible HTML prose. Flag contradictory values as degrading defects.

5. **Locked Facts in Non-Text Carriers**:
   - Flag meaningful factual images (charts, pricing tables, infographics) lacking descriptive `alt` text.
   - Detect facts locked in PDF links (`pricing.pdf`, `spec.pdf`) **only** when equivalent readable HTML text is missing or insufficient on the page.

## Output
`{"findings": [...], "opportunities": [...]}` conforming to the shared Adobe Hackathon schema.
