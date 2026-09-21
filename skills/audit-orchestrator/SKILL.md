---
name: audit-orchestrator
description: Entrypoint for the Aura-Vision-GEO marketplace. Given a website, runs crawl-and-render-audit, structured-fact-audit, trust-and-corroboration-audit, and engagement-audit, then merges their findings into one deduplicated, consistently-scored report against the fixed schema. Use this skill when asked to "audit <site> for AI visibility / discoverability / engagement", or when composing the outputs of the four worker skills into a final deliverable.
license: MIT
allowed-tools: [bash, read_file, write_file]
---

# Audit Orchestrator (entrypoint)

## When to use
Invoke this skill whenever a user asks for a full AuraVision GEO / AI-discoverability / on-site-engagement audit of a website (a URL or bare domain). This is the only skill in the marketplace a caller should invoke directly — it invokes the four worker skills itself and is responsible for the final report.

## Inputs
- `site` (required): a URL or domain, e.g. `https://example.com` or `example.com`. Normalize to a scheme-qualified root URL before dispatch (default `https://`, follow one redirect if the root 404s on https).
- `max_pages` (optional, default 12): cap on how many internal pages the crawler may fetch. Keeps total runtime under the 5-minute budget.
- `out` (optional, default `audit_report`): output basename for generated report deliverables (`.json`, `.md`, `.html`).
- `focus` (optional): `discoverability`, `engagement`, or `both` (default `both`). If set, skip the worker skills not relevant to the focus.

## Procedure (deterministic)

1. **Normalize the input.** Resolve `site` to a single root URL. Fail fast with an access limitation diagnostic finding (`id: F-001`, category `discoverability`, subcategory `crawlability`, severity `critical`) if zero valid HTML pages can be retrieved — do not proceed to worker skills against a dead or inaccessible site.

2. **Fetch once, share the fetch.** Perform one raw HTTP GET of the homepage and up to `max_pages` internal pages (same-origin only, respecting `robots.txt` disallow rules parsed by the orchestrator crawler). Pass this shared page set (URL, status, headers, raw HTML) to every worker skill so no site is fetched four separate times. This is what keeps a "typical website" audit under 5 minutes.

3. **Dispatch worker skills** (skip any excluded by `focus`):
   - `crawl-and-render-audit` → off-site discoverability, layer 1–2 (crawler admitted, content readable)
   - `structured-fact-audit` → off-site discoverability, layer 3 (facts extractable and machine-parseable)
   - `trust-and-corroboration-audit` → off-site discoverability, cross-web trust + entity disambiguation + freshness
   - `engagement-audit` → on-site engagement
   Each worker skill returns a list of raw findings in the shared finding shape (see `references/schema.md`) plus a list of proactive/beyond-defect suggestions.

4. **Merge and dedupe.** Concatenate all findings. Two findings are duplicates if they share `category` + point at the same root cause (e.g. both a general "no structured data" and a "no Product schema" finding from different skills on the same pages collapse into one, keeping the more specific title and the union of evidence). Prefer the higher-confidence evidence when merging.

5. **Normalize severity** against the shared rubric in `references/schema.md` — do not trust a worker skill's self-assigned severity blindly; re-derive it from the finding's `impact` (does it block extraction entirely, or degrade it?) and `scope` (one page vs. site-wide) fields so severities are comparable across categories. Run `scripts/aggregate_report.py` to do this mechanically rather than re-judging by feel.

6. **Assign sequential IDs** `F-001, F-002, …` ordered by severity (critical → high → medium → low), then by confidence, then by category.

7. **Fold in proactive suggestions** that don't correspond to a detected defect into a separate `opportunities` array with the shape `{title, suggested_action}` (where `suggested_action` contains `summary` and `priority`). Unlike findings, opportunity objects do not have a `severity` field (nor `id`, `category`, `evidence`), as they are additive recommendations rather than evidence-backed defects.

8. **Emit the report**: write `audit_report.json` matching `references/schema.md` exactly (required fields present, extra fields allowed), an executive brief `audit_report.md` (one paragraph per finding: what's wrong, why it matters for AI visibility or engagement, exactly how to fix it) for a non-expert to act on, and an interactive `audit_report.html` visual dashboard.

## Output
Deliverables per audit run (default basename `audit_report`, configurable via `--out`):
- `audit_report.json` — machine-readable, matches the fixed schema (see `references/schema.md`).
- `audit_report.md` — the same content, prose-rendered, grouped by severity then category.
- `audit_report.html` — interactive visual dashboard for executive review.

Never modify the audited site. Every worker skill is read-only; this skill only reads their outputs and writes the report files.
