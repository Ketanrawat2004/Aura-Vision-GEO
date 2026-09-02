---
name: engagement-audit
description: Checks why a visitor who successfully arrives at a page might not stay — missing above-the-fold orientation (what is this / who is it for), unclear navigation, broken internal links leading to dead ends, unlabeled or generic calls-to-action, no mobile viewport, walls of unscannable text, and missing basic trust signals (contact info, about page). Use for the on-site-engagement half of the audit, independent of the three discoverability worker skills.
license: MIT
allowed-tools: [bash, http_fetch]
---

# On-Site Engagement Audit

## When to use
Called by `audit-orchestrator`. This is the only worker skill that doesn't
map to the discoverability appendix (A–D) — it covers "on-site engagement:
keeping the visitor once they arrive," the other half of the brief. Several
of its checks (clear orientation, scannable structure) are worth noting as
overlapping with what helps a machine extractor too — a page that's
confusing to a human skimmer is often also poorly structured for a machine —
but don't conflate the two categories in the report; keep engagement
findings under `category: "engagement"`.

## Inputs
Shared page set from the orchestrator.

## Procedure

1. **Above-the-fold orientation.** For the homepage (and any landing page),
   check whether the first ~150 words of visible text answer "what is this
   / who is it for" — look for a clear one-line description near the top
   (commonly an `<h1>` + adjacent paragraph). If the first substantial text
   block is generic (a hero image caption with no description, a slogan with
   no explanation of what the company does) flag `degrading`/`single-page`.

2. **Navigation structure** (`scripts/check_engagement.py`): confirm a
   `<nav>` element or an unordered list of internal links near the top of
   the page exists, and that internal links use descriptive text (not just
   "here"/"this"/"click"). No nav on a multi-page site is `degrading`/`sitewide`.

3. **Dead ends.** Sample a handful of internal links found on the audited
   pages (respecting `max_pages`/robots.txt, same constraint as
   `crawl-and-render-audit`) and check their response status. A cluster of
   4xx/5xx internal links is `degrading`/`section` (or `sitewide` if spread
   across every sampled page).

4. **CTA clarity.** Collect button/link text that looks like a
   call-to-action (`<button>`, `<a class*="btn">`, or link text near a form).
   Generic, context-free text ("Click here", "Submit", "Learn more" with
   nothing nearby to learn more *about*) is `cosmetic`; if it's the *only*
   CTA on a conversion-relevant page (pricing, signup) it's `degrading`/`single-page`.

5. **Mobile viewport.** Missing `<meta name="viewport">` is `degrading`/`sitewide`
   if absent on every sampled page — a strong, cheap, binary signal.

6. **Scannability.** Average words-per-`<p>` across the page; a page whose
   paragraphs average well above ~120 words with no subheadings breaking
   them up is `cosmetic`/`section` (readable is subjective past a point —
   keep this as a soft signal, not a hard rule, and don't flag short-form
   content like a single product blurb).

7. **Basic trust signals.** No visible way to find contact info or an
   about/company page from primary navigation is `degrading`/`sitewide` —
   this affects both a human's willingness to trust the site and (per
   `trust-and-corroboration-audit`) the entity-disambiguation signals
   available to a machine.

## Output
`{"findings": [...], "opportunities": [...]}`, `category: "engagement"` on
every finding. Typical opportunities: adding a search box, breadcrumbs on
deep pages, a persistent primary CTA.
