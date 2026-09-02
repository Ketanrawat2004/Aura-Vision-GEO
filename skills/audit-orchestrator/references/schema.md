# Shared report schema & severity rubric

Every worker skill must emit findings in this shape before handing them to the
orchestrator. This file is the single source of truth for severity — worker
skills propose `impact`/`scope`, the orchestrator derives the final `severity`.

## Finding shape (worker output, pre-merge)

```json
{
  "title": "No JSON-LD structured data on product pages",
  "category": "discoverability",          // discoverability | engagement
  "subcategory": "structured-data",        // crawlability | rendering | structured-data |
                                            // freshness | corroboration | entity | navigation |
                                            // orientation | performance | trust-signals
  "impact": "blocking",                    // blocking | degrading | cosmetic
  "scope": "sitewide",                     // sitewide | section | single-page
  "confidence": "high",                    // high | medium | low — how sure the check is,
                                            // not how bad the problem is
  "evidence": "Crawled 12 product pages; 0/12 contain schema.org markup.",
  "suggested_action": {
    "summary": "Add Product/Offer JSON-LD to every product page.",
    "priority": "high",
    "mechanism": "Why this fixes it: assistants extract structured facts (price, availability) from JSON-LD far more reliably than from prose; this closes the gap at the source rather than hoping the summarizer parses free text correctly."
  }
}
```

## Severity derivation (orchestrator applies this, not the worker skill)

| impact \ scope | sitewide | section | single-page |
|---|---|---|---|
| blocking | critical | high | high |
| degrading | high | medium | medium |
| cosmetic | medium | low | low |

- **blocking** = the fact/page is not extractable *at all* by a system with that
  limitation (e.g. robots.txt disallows all known AI-crawler UAs; homepage
  ships an empty `<div id="root">` with no server-rendered fallback).
- **degrading** = extractable but unreliable, ambiguous, or low-confidence
  (facts present only in prose, not structured; single-sourced claim with no
  corroboration; stale date next to an evergreen claim).
- **cosmetic** = would strengthen things but nothing is currently broken
  (missing alt text on non-critical images, thin meta description).

`confidence` never changes the severity — it's surfaced separately so a
reviewer can tell "definitely broken, definitely bad" apart from "probably
worth checking." Never silently upgrade a low-confidence finding to raise its
apparent severity; report it as `medium/low confidence` instead of inflating
`impact`.

## Real-World Empirical Calibration Notes

From testing across 10 production web properties (Stripe, Cloudflare, Vercel, MDN, NYTimes, Reddit, Medium, IKEA, Linear, Basecamp):

1. **`critical` Severity Calibration**:
   - Appropriately triggered on `nytimes.com` (robots.txt blocking 9 named AI crawlers sitewide) and `reddit.com` (`Disallow: /` sitewide for `*` and AI bots).
   - Prevents false-positive `critical` ratings on `medium.com` by isolating WAF challenge 403s from application-level `noindex` tags.

2. **`high` Severity Calibration**:
   - Appropriately derived for `degrading/sitewide` structured data omissions (e.g. missing `Product`/`Offer` schema across high-traffic pricing pages on Stripe, Vercel, Linear).
   - Appropriately derived for entity disambiguation risks on common-noun brand names (e.g. Linear) lacking `sameAs` linkage.

3. **`medium` / `low` Severity Calibration**:
   - Appropriately applied to formatting and structure nuances, such as multi-`<h1>` responsive elements or missing `<nav>` tags on isolated subpages.

## Final report shape (orchestrator output — the required floor)

```json
{
  "site": "example.com",
  "audited_at": "2026-09-20T14:32:00Z",
  "summary": {
    "total_findings": 6,
    "critical": 1,
    "high": 2,
    "medium": 3,
    "low": 0
  },
  "findings": [
    {
      "id": "F-001",
      "title": "No JSON-LD structured data on product pages",
      "severity": "high",
      "category": "discoverability",
      "evidence": "Crawled 12 product pages; 0/12 contain schema.org markup.",
      "suggested_action": {
        "summary": "Add Product/Offer JSON-LD to every product page.",
        "priority": "high"
      }
    }
  ],
  "opportunities": [
    {
      "title": "Publish an llms.txt at the site root",
      "suggested_action": {
        "summary": "Add /llms.txt pointing AI agents at your canonical facts pages.",
        "priority": "low"
      }
    }
  ]
}
```

`findings[].id`, `.title`, `.severity`, `.evidence`, `.suggested_action` are
the required floor per the brief — everything else here is additive.
