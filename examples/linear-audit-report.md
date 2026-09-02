# AuraVision GEO Audit  https://linear.app

Audited at 2026-09-02T13:40:15Z

**1 findings**  0 critical, 0 high, 1 medium, 0 low

## [MEDIUM] F-001: Page implies Product content but has no Product structured data
*Category: discoverability  Confidence: medium*

**Evidence:** Content-based signal detected for Product (e.g. price pattern or FAQ-shaped headings) but @type=Product absent from JSON-LD on https://linear.app. Types actually present: none.

**Fix (high priority):** Add Product JSON-LD matching what the page already says in prose.
> Why: Structured data is what an assistant quotes from directly; prose alone requires the extractor to correctly parse free text, which is far less reliable.
