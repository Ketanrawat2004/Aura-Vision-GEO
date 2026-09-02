---
name: crawl-and-render-audit
description: Checks whether AI crawlers and answer-engine fetchers can even reach a site's pages and read what's on them — robots.txt rules against named AI-agent user agents, sitemap presence/freshness, meta-robots blocks, and the gap between what a plain HTTP GET sees versus what a rendered browser sees (JS-only content). Use for the "is the crawler let in, can it read the page" half of an AI-discoverability audit.
license: MIT
allowed-tools: [bash, http_fetch]
---

# Crawl & Render Audit

## When to use
Called by `audit-orchestrator` as one of four worker skills. Covers Appendix A
("three things have to succeed in order: crawler let in, page readable, fact
extractable") layers 1 and 2 — layer 3 (fact extraction from readable text)
belongs to `structured-fact-audit`.

## Inputs
- The shared page set from the orchestrator (homepage + up to `max_pages`
  internal pages, raw HTML + response headers already fetched).
- `site` root URL.

## Procedure

1. **Fetch and parse `robots.txt`** at the site root (`scripts/check_crawlability.py`).
   Check the rules against a fixed list of known AI-agent user-agent tokens
   (GPTBot, OAI-SearchBot, ChatGPT-User, ClaudeBot, anthropic-ai, Claude-Web,
   PerplexityBot, Google-Extended, CCBot, Bytespider, Amazonbot,
   Applebot-Extended) as well as `*`. Flag any full-site `Disallow: /` against
   a named AI agent as **blocking/sitewide**; a disallow on a specific path
   (e.g. `/blog/`) that overlaps a page the audit was asked about is
   **blocking/section**. This is a static read of robots.txt — never send
   requests that impersonate a blocked agent to test whether the block is
   enforced; that would be evading a published access rule the site owner
   set on purpose. The check must also **respect** these same rules for its
   own fetching: never crawl a path this skill's own `*`-agent rule
   disallows.

2. **Check `sitemap.xml`.** Look for a `Sitemap:` line in robots.txt, else try
   `/sitemap.xml`. If present, sample `<lastmod>` values — if the newest
   `lastmod` across the whole sitemap is >12 months old while the site's
   visible copyright/footer year is current, flag a **degrading/sitewide**
   freshness-adjacent crawlability issue (the sitemap is telling crawlers
   nothing has changed). If absent entirely, that's **degrading/sitewide**
   (not blocking — crawlers can still discover pages by following links, just
   less reliably).

3. **Check meta-robots and `X-Robots-Tag`.** Scan fetched pages for
   `<meta name="robots" content="noindex">` or an `X-Robots-Tag: noindex`
   response header on pages that are clearly meant to be public (not
   `/admin`, `/checkout`, etc.). A `noindex` on a public money-page (pricing,
   product, docs) is **blocking/single-page** or **blocking/section** if it
   recurs across a template.

4. **Detect the render gap** (`scripts/check_render_gap.py`). For each fetched
   page: strip `<script>`/`<style>`, extract visible text length from the raw
   HTML. Separately, look for known SPA-shell fingerprints (`<div id="root">`,
   `<div id="app">`, a `<body>` whose only child is a single near-empty div,
   heavy `<script type="module">` bundles with almost no server-rendered
   text). If a headless-render tool is available in the execution
   environment, render the page and compare rendered-vs-raw text length; a
   ratio above ~3x, or key facts (price, spec, contact info patterns) present
   only in the rendered version, is **blocking/single-page** (or
   **sitewide** if the shell pattern repeats across every sampled page — that
   means the whole site is client-rendered with no fallback). If no
   headless-render tool is available, downgrade the same finding to
   `confidence: "low"` and say explicitly in the evidence that it's a static
   heuristic, not a confirmed render diff — never report a render-gap finding
   at `confidence: "high"` without an actual rendered comparison.

5. Emit findings + opportunities in the shared shape (`../audit-orchestrator/references/schema.md`).
   Typical opportunities even with no defect: prerendering/SSR for the
   heaviest JS routes, an explicit `Sitemap:` line in robots.txt if one
   exists but isn't referenced there.

## Output
`{"findings": [...], "opportunities": [...]}` written to a JSON file the
orchestrator passes to `aggregate_report.py`.
