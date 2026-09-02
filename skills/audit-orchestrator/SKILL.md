---
name: audit-orchestrator
description: Entrypoint for the ai-visibility-audit marketplace. Given a website, runs crawl-and-render-audit, structured-fact-audit, trust-and-corroboration-audit, and engagement-audit, then merges their findings into one deduplicated, consistently-scored report against the fixed schema. Use this skill when asked to "audit <site> for AI visibility / discoverability / engagement", or when composing the outputs of the four worker skills into a final deliverable.
license: MIT
allowed-tools: [bash, read_file, write_file]
---

# Audit Orchestrator (entrypoint)

## When to use
Invoke this skill whenever a user asks for a full AI-visibility / AI-discoverability / on-site-engagement audit of a website (a URL or bare domain). This is the only skill in the marketplace a caller should invoke directly — it invokes the four worker skills itself and is responsible for the final report.

## Inputs
- `site` (required): a URL or domain, e.g. `https://example.com` or `example.com`. Normalize to a scheme-qualified root URL before dispatch (default `https://`, follow one redirect if the root 404s on https).
- `max_pages` (optional, default 15): cap on how many pages any worker skill may fetch. Keeps total runtime under the 5-minute budget.
- `focus` (optional): `discoverability`, `engagement`, or `both` (default `both`). If set, skip the worker skills not relevant to the focus.

## Procedure (deterministic)

1. **Normalize the input.** Resolve `site` to a single root URL. Fail fast with a `critical` finding (`id: F-000`, category `access`) if the root URL is unreachable after 2 retries — do not proceed to the worker skills against a dead site.

2. **Fetch once, share the fetch.** Perform one raw HTTP GET of the homepage and up to `max_pages` internal pages (same-registrable-domain only, respecting `robots.txt` disallow rules — see crawl-and-render-audit for the parsing logic). Pass this shared page set (URL, status, headers, raw HTML) to every worker skill so no site is fetched four separate times. This is what keeps a "typical website" audit under 5 minutes.

3. **Dispatch worker skills** (skip any excluded by `focus`):
   - `crawl-and-render-audit` → off-site discoverability, layer 1–2 (crawler admitted, content readable)
   - `structured-fact-audit` → off-site discoverability, layer 3 (facts extractable and machine-parseable)
   - `trust-and-corroboration-audit` → off-site discoverability, cross-web trust + entity disambiguation + freshness
   - `engagement-audit` → on-site engagement
   Each worker skill returns a list of raw findings in the shared finding shape (see `references/schema.md`) plus a list of proactive/beyond-defect suggestions.

4. **Merge and dedupe.** Concatenate all findings. Two findings are duplicates if they share `category` + point at the same root cause (e.g. both a general "no structured data" and a "no Product schema" finding from different skills on the same pages collapse into one, keeping the more specific title and the union of evidence). Prefer the higher-confidence evidence when merging.

5. **Normalize severity** against the shared rubric in `references/schema.md` — do not trust a worker skill's self-assigned severity blindly; re-derive it from the finding's `impact` (does it block extraction entirely, or degrade it?) and `scope` (one page vs. site-wide) fields so severities are comparable across categories. Run `scripts/aggregate_report.py` to do this mechanically rather than re-judging by feel.

6. **Assign sequential IDs** `F-001, F-002, …` ordered by severity (critical → high → medium → low), then by category.

7. **Fold in proactive suggestions** that don't correspond to a detected defect as `suggested_action`-only entries with `severity: "opportunity"` (outside the four required severities, additive) in a separate `opportunities` array — required findings must all have real evidence; opportunities may be recommendations with no defect behind them.

8. **Emit the report**: write `audit_report.json` matching `references/schema.md` exactly (required fields present, extra fields allowed), and a human-readable `audit_report.md` (one paragraph per finding: what's wrong, why it matters for AI visibility or engagement, exactly how to fix it) for a non-expert to act on.

## Output
Two artifacts per audit run:
- `audit_report.json` — machine-readable, matches the fixed schema (see `references/schema.md`).
- `audit_report.md` — the same content, prose-rendered, grouped by severity then category.

Never modify the audited site. Every worker skill is read-only; this skill only reads their outputs and writes the two report files.
