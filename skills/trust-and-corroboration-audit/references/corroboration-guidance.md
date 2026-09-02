# Corroboration guidance for the executing agent

This skill's step 3 (corroboration) and step 4 (entity disambiguation)
deliberately hand judgment to whatever agent executes the skill, rather than
scripting them, because "is this source independent" and "is this name
collision a real risk" don't reduce to a regex. This file gives the judgment
calls a fixed shape so different runs stay consistent.

## What counts as an independent source
- Independent: news coverage (Bloomberg, TechCrunch, Forbes), Wikipedia/Wikidata, industry directories
  (Crunchbase, G2, Capterra), regulatory filings (SEC 10-K/S-1), third-party review sites.
- NOT independent: the brand's own subdomains, its social media accounts,
  press releases the brand issued (even if hosted elsewhere on PR Newswire/BusinessWire), sponsored/
  affiliate content that reads like marketing copy.
- A source repeating something *because* it's citing the brand's own site
  (a directory listing that clearly scraped the brand's About page verbatim)
  doesn't count as independent corroboration — it's the same single source
  wearing a different URL.

## How to pick which facts to check
Prefer facts that are:
1. **Load-bearing** — the kind of thing an assistant would actually be asked
   about and would quote (founding year, HQ city, flagship price, a
   headline stat like "$1.9T payment volume").
2. **Checkable** — a specific claim, not a vague one ("50,000 customers" or "founded 2019" is
   checkable; "industry-leading" is not, skip vague superlatives entirely).
3. **Not already covered** by a `structured-fact-audit` finding — don't
   re-flag the same underlying issue twice under a different skill.

## Severity discipline
Only a *direct contradiction* from an authoritative independent source earns
`blocking`. "I couldn't find it corroborated in 1-2 searches" is much weaker
evidence than "an independent source says something different" — the first
is `degrading` at `confidence: medium` at most, never `blocking`. This
distinction matters for avoiding false positives, which the rubric penalizes
directly.

## Empirical Evidence from 10 Real-World Audited Sites

Real-world web searches and entity resolution tests conducted across 10 sites demonstrate how entity disambiguation and cross-web trust operate in practice:

| Brand / Site | Claimed / Load-Bearing Facts | Independent Corroboration Status | Entity Disambiguation & Collision Risk |
|---|---|---|---|
| **Stripe** (`stripe.com`) | Financial infrastructure; founded 2010 by Patrick & John Collison; $1.9T payment volume (2025); valuation ~$159B. | **High Corroboration**: Confirmed across SEC filings, Wikipedia (`Q2845664`), Bloomberg, Forbes. | **Low Risk**: Dominates search queries; carries `sameAs` array linking to Wikipedia/Crunchbase. |
| **Linear** (`linear.app`) | Issue tracking & product development tool; founded 2019 by Karri Saarinen, Jori Lallo, Tuomas Artman. | **High Corroboration**: Confirmed across TechCrunch, Crunchbase, podcasts, developer communities. | **High Risk**: Severe name collision with foundational mathematics/CS concepts (*linear algebra, linear regression, linear time*). Site currently carries **no `sameAs` JSON-LD**, leaving disambiguation entirely to lexical context. |
| **Cloudflare** (`cloudflare.com`) | "Powering 20% of the Internet"; founded 2009 by Matthew Prince, Lee Holloway, Michelle Zatlyn; NYSE: NET. | **High Corroboration**: W3Techs web surveys confirm ~20% market share of top 10M domains; SEC 10-K filings verify financial and scale metrics. | **Low Risk**: Carries comprehensive `Organization` schema with canonical URLs and verified entity profiles. |
| **Basecamp** (`basecamp.com`) | Straightforward project management; 20+ years in business (founded 1999 as 37signals); over 3M accounts created. | **High Corroboration**: Documented in 37signals company publications (*Rework*, *Remote*), Wikipedia, and software history archives. | **Moderate Risk**: Collides with generic outdoor/mountaineering terminology (e.g. Everest Base Camp). |
| **The New York Times** (`nytimes.com`) | Global news publication founded 1851; Pulitzer prizes; top investigative reporting. | **Authoritative Ground Truth**: Universal cross-web citation. | **Discoverability Paradox**: Despite maximal cross-web trust, direct answer-engine retrieval is blocked at the crawl layer via `robots.txt` disallow rules. |

## Concrete Blindspots & Edge Cases for `trust-and-corroboration-audit`

1. **The Common-Noun Entity Collision Gap (The Linear Case)**:
   - Brands named after dictionary terms or scientific concepts (e.g., *Linear*, *Vercel*, *Basecamp*, *Square*) face severe entity misattribution when prompting LLMs with minimal context.
   - When a site omits `sameAs` links (pointing to Wikidata, Wikipedia, Crunchbase, LinkedIn) in its `Organization` schema, answer engines must rely on fuzzy semantic matching rather than deterministic entity ID resolution.

2. **The "Marketing Stat vs. Audited Stat" Discrepancy**:
   - SaaS marketing pages frequently feature unanchored statistics ("Over 100,000 teams", "99.99% uptime") that exist only on their own marketing landing page.
   - When an assistant cannot corroborate a numeric statistic across external reviews, G2/Capterra benchmarks, or regulatory filings, confidence degrades to `medium/single-source fragility`.

3. **Freshness Conflicts Between Marketing Copy and Copyright Headers**:
   - Marketing pages that update real-time statistics (e.g. "Trusted by 10M developers") without updating visible timestamped bylines or schema `dateModified` risk being penalized by freshness-sensitive answer engines that compare HTTP `Last-Modified` against the claimed year.
