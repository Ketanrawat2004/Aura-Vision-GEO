---
name: structured-fact-audit
description: Checks whether the facts on a readable page are actually extractable by a machine — JSON-LD/schema.org presence and validity against what the page's own content implies it should carry (prices imply Product/Offer, Q&A content implies FAQPage), heading structure, and facts that exist only inside non-text carriers (images, PDFs, video) with no plain-text equivalent. Use for the "can the crawler pick out the specific fact" half of an AI-discoverability audit, once crawl-and-render-audit has confirmed the page is reachable and readable.
license: MIT
allowed-tools: [bash, http_fetch]
---

# Structured & Extractable Facts Audit

## When to use
Called by `audit-orchestrator`. Covers Appendix A layer 3 and Appendix C
("the more explicitly and unambiguously a fact is stated in plain, readable
text, the more likely a machine extracts it correctly; the more it's
implied, buried, or locked inside something non-textual, the more likely
it's missed").

## Inputs
Shared page set from the orchestrator (raw HTML per page).

## Procedure

1. **Extract every JSON-LD block** (`scripts/check_structured_data.py`) from
   each page — handle bare objects, arrays of objects, and `@graph` wrappers.
   Collect the set of `@type` values present per page.

2. **Infer what the page implies it should carry**, from its own visible text
   — don't check against a fixed checklist per URL path, check against what
   the content itself signals (this is what makes the check generalize to
   unseen sites):
   - Currency-like patterns (`$12`, `₹999`, `€49.99`) anywhere in the visible
     text → the page is describing something purchasable → expect
     `Product`/`Offer` (or `Service`) schema with a machine-readable price.
   - A cluster of heading-or-bold text ending in `?` followed by explanatory
     text → the page is FAQ-shaped → expect `FAQPage`/`Question`/`Answer`.
   - The homepage, or any page with a clear brand/company name in the title →
     expect `Organization` (name, url, and ideally `sameAs` — see
     `trust-and-corroboration-audit` for why `sameAs` matters).
   - A dated byline or "posted on" pattern → expect `Article`/`BlogPosting`
     with `datePublished`.
   Where the implied type is present but missing required properties (e.g. a
   `Product` node with no `offers`), that's still a finding — partial
   structured data that's silently invalid is easy to miss by eye.

3. **Validate what's minimally required per type present** (not full
   schema.org conformance — just the properties an assistant actually needs
   to quote a fact): `Organization` → `name`+`url`; `Product` → `name`+
   `offers` (or a price-bearing `Offer`); `FAQPage` → `mainEntity[]` each with
   `name`+`acceptedAnswer.text`; `Article` → `headline`+`datePublished`.

4. **Detect facts locked in non-text carriers.** Flag:
   - A price/spec/contact pattern that appears to live only inside an `<img>`
     with empty or missing `alt` text (the visible-text extraction has
     nothing for it).
   - A link to a PDF/PPT whose anchor text suggests it's the *only* copy of
     something important (`pricing`, `spec sheet`, `brochure`, `menu`,
     `datasheet`) with no on-page text equivalent.
   These are `degrading`, scope depends on how central the page is (a locked
   pricing PDF on the pricing page is `section`, at minimum).

5. **Check heading structure**: exactly one `<h1>` per page is the target;
   zero or multiple is a `cosmetic`/`degrading` finding depending on how far
   off it is — this affects how cleanly a page can be chunked for extraction,
   not just SEO convention.

## Output
`{"findings": [...], "opportunities": [...]}`. Typical opportunities even
with valid schema present: adding `FAQPage` markup for genuinely-FAQ-shaped
content that isn't yet marked up, adding `sameAs` links on `Organization` to
feed `trust-and-corroboration-audit`'s entity-disambiguation check.
