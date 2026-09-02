---
name: trust-and-corroboration-audit
description: Checks whether a brand's key facts are corroborated across independent sources and whether the brand name is disambiguated from unrelated entities, plus whether visible content is actually stale despite claiming to be current. Use for the "does the wider web agree, and is this brand identifiable" half of an AI-discoverability audit — the part that can't be answered from the site alone. Requires a web-search-capable execution agent for the corroboration and disambiguation steps.
license: MIT
allowed-tools: [bash, http_fetch, web_search]
---

# Trust, Corroboration & Entity-Disambiguation Audit

## When to use
Called by `audit-orchestrator`. Covers Appendix D ("machines tend to treat a
fact as more trustworthy when many independent places say the same thing...
a related problem is mistaken identity") and the freshness half of Appendix C.

Unlike the other three worker skills, part of this one's procedure requires
the **executing agent's own web-search tool**, not just fetching the target
site — corroboration is inherently a comparison across sources the skill
doesn't control. `scripts/check_freshness.py` handles everything that's
deterministic and local (dates, headers); steps 3–4 below are instructions
for the agent, not a script, because they require judgment about source
independence and name-collision risk that a fixed script can't generalize.

## Inputs
- Shared page set (for local freshness signals).
- `brand_name`: extracted from the site's `Organization` schema `name`, or
  the site title, if not otherwise given.

## Procedure

1. **Local freshness check** (`scripts/check_freshness.py`): compare the
   HTTP `Last-Modified` header, any visible "updated on"/"posted on" date in
   the text, and the sitemap `lastmod` (from `crawl-and-render-audit`'s
   output, reused rather than re-fetched) against each other and against
   today. Flag as `degrading` when a page makes an evergreen-sounding claim
   (no explicit "as of" qualifier) but every date signal on it is >18 months
   old — the risk isn't that it's old, it's that it's stated as if current.

2. **Pick 2–4 load-bearing facts to check**, not everything on the page —
   the kind of fact an assistant would actually quote (founding year,
   headquarters, flagship product name/price, a specific claimed stat like
   "50,000 customers"). Picking facts is a judgment call for the executing
   agent based on what the page emphasizes; don't hardcode a fact list.

3. **Corroboration**: for each picked fact, run one targeted web search (the
   agent's own `web_search` tool) for the fact plus the brand name. Classify
   the result:
   - Confirmed by ≥2 sources independent of the brand's own site/social
     accounts → no finding, this fact is fine.
   - Found nowhere but the brand's own site → `degrading`/`single-page` (or
     `section` if it's a fact repeated verbatim across many of the brand's
     own pages but nowhere off-site) — "single-source fragility."
     `confidence: "medium"` (absence-of-evidence from a handful of searches
     isn't proof, say so in the evidence).
   - Contradicted by an independent source (different founding year,
     different HQ) → `blocking`/`single-page`, `confidence: "high"` if the
     contradiction is direct and the independent source looks authoritative
     (news, Wikipedia, official filings) — this is the one case in this
     skill allowed to reach `blocking`, because a contradicted fact can get
     actively misreported, not just omitted.
   Cap this step at 4 searches total — the 5-minute budget doesn't allow
   exhaustive fact-checking, and the brief only expects patterns, not a full
   research report.

4. **Entity disambiguation**: search the bare brand name. If the results are
   dominated by unrelated entities (a common word, another company, a
   public figure) and the site's own `Organization` schema has no `sameAs`
   links (Wikipedia, Crunchbase, LinkedIn, Wikidata) and no disambiguating
   qualifier appears near the first mention of the brand name on the
   homepage (e.g. an industry/location qualifier), flag `degrading`/`sitewide`
   — this is a systemic risk, not a single-page issue.

## Output
`{"findings": [...], "opportunities": [...]}`. Typical opportunities: adding
`sameAs` even when disambiguation isn't currently a problem (cheap
insurance), publishing a citable stats/about page consolidating the facts
that are currently single-sourced.
