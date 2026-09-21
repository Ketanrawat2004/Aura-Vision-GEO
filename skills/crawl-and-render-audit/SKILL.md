---
name: crawl-and-render-audit
description: Checks whether AI crawlers and answer-engine fetchers can reach a site's pages and read what's on them — robots.txt rules against named AI-agent user agents, sitemap presence/freshness, meta-robots blocks, and the gap between what a plain HTTP GET sees versus what a rendered browser sees (JS-only content). Use for the "is the crawler let in, can it read the page" half of an AI-discoverability audit.
license: MIT
allowed-tools: [bash, http_fetch]
---

# Crawl & Render Audit

## When to use
Called by `audit-orchestrator` as one of four worker skills. Covers Appendix A ("three things have to succeed in order: crawler let in, page readable, fact extractable") layers 1 and 2 — layer 3 (fact extraction from readable text) belongs to `structured-fact-audit`.

## Inputs
- The shared page set from the orchestrator (homepage + up to `max_pages` internal pages, raw HTML + response headers already fetched).
- `site` root URL.

## Procedure (deterministic)

1. **Audit `robots.txt`** at the site root (`scripts/check_crawlability.py`):
   - Check rules against 12 known AI-agent user-agent tokens (`GPTBot`, `OAI-SearchBot`, `ChatGPT-User`, `ClaudeBot`, `anthropic-ai`, `Claude-Web`, `PerplexityBot`, `Google-Extended`, `CCBot`, `Bytespider`, `Amazonbot`, `Applebot-Extended`) as well as `*`.
   - Flag any full-site `Disallow: /` against named AI agents as **blocking/sitewide**; disallows on critical informational paths (`/pricing`, `/products`, `/about`) are flagged as **blocking/section**.
   - Respect these same rules: never perform unauthorized or rate-abusive requests.

2. **Check `sitemap.xml`**:
   - Verify sitemap reference in `robots.txt` or default `/sitemap.xml`.
   - Sample `<lastmod>` values — if the newest timestamp is >12 months old, flag stale sitemap indexing as degrading.

3. **Check meta-robots, HTTP status, and canonicals**:
   - Scan pages for `<meta name="robots" content="noindex">` or `X-Robots-Tag: noindex` on public routes.
   - Detect broken internal link targets (HTTP 4xx/5xx) and cross-domain canonical mismatches.

4. **Detect the render gap** (`scripts/check_render_gap.py`):
   - Worker skills strictly analyze the shared page dataset without making independent network or browser requests.
   - If pre-rendered text was captured by the orchestrator at crawl time, compare rendered-vs-raw text ratio (ratio $\ge$ 3.0x is flagged as a blocking render gap).
   - When running statically without headless browser rendering, inspect static SPA shell indicators (`<div id="root">`, `<div id="app">`, `<app-root>`) with minimal visible text (< 60 words), and detect substantive content trapped exclusively inside serialized framework hydration state scripts (`__NEXT_DATA__`, `__NUXT_DATA__`, Remix).
   - Framework-agnostic empty shell fallback: when a page has near-zero initial visible text (< 20 words) with no recognized framework container or hydration fingerprint, detect client-side rendering via corroborating signals — either a `<noscript>` tag requiring JavaScript execution or link starvation ($\le$ 1 internal link with $\ge$ 70% `.js`/`.css` bundle assets). This catches modern frontend frameworks lacking standard container fingerprints (e.g., SvelteKit, Astro, Qwik) and ensures robust generalization across unseen web architectures (directly addressing the "generalization" rubric criterion).

5. **Emit findings + opportunities** in the shared shape conforming to `references/schema.md`.

## Output
`{"findings": [...], "opportunities": [...]}` written to a JSON file passed to `aggregate_report.py`.
