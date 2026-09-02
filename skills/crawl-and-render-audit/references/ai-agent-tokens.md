# Known AI / answer-engine crawler user-agent tokens

Checked by `scripts/check_crawlability.py`. This list is intentionally a
plain data file, not hardcoded prose in SKILL.md, so it can be updated as
new agents ship without touching the skill's instructions.

| Token | Operator | Purpose |
|---|---|---|
| GPTBot | OpenAI | Training/crawling |
| OAI-SearchBot | OpenAI | Powers ChatGPT search citations |
| ChatGPT-User | OpenAI | Live fetch during a ChatGPT session (plugins/browsing) |
| ClaudeBot | Anthropic | Training/crawling |
| anthropic-ai | Anthropic | Legacy token, still honored by some sites |
| Claude-Web | Anthropic | Live fetch during a Claude session |
| PerplexityBot | Perplexity | Crawling + live citation fetch |
| Google-Extended | Google | Opts a site in/out of Gemini/AI Overviews training & grounding, separate from classic Googlebot |
| CCBot | Common Crawl | Feeds many downstream LLM training sets |
| Bytespider | ByteDance | Training/crawling |
| Amazonbot | Amazon | Alexa/Rufus-related crawling |
| Applebot-Extended | Apple | Apple Intelligence training/grounding opt-out signal |

## Why check these explicitly instead of just '*'

A site can allow `*` (so it looks "open" at a glance) while carrying a
specific `Disallow: /` block for `GPTBot` or `Google-Extended` further down
the file — `robots.txt` groups are agent-specific and the most specific
matching group wins. `urllib.robotparser.RobotFileParser.can_fetch(agent, url)`
resolves this correctly per agent, which is why the script checks each token
individually rather than reading the `*` group alone.

## Empirical Evidence from 10 Real-World Audited Sites

During audit testing across 10 diverse production web properties (high-citation tech brands vs. media, platforms, and blocked properties), the following live bot permission matrix was observed:

| Site / Brand | `*` | GPTBot | ClaudeBot | PerplexityBot | Google-Extended | OAI-SearchBot | CCBot | Sitemaps in robots.txt | `/llms.txt` |
|---|---|---|---|---|---|---|---|---|---|
| **Stripe** (`stripe.com`) | ALLOWED | ALLOWED | ALLOWED | ALLOWED | ALLOWED | ALLOWED | ALLOWED | `sitemap.xml` | Present |
| **MDN Web Docs** (`developer.mozilla.org`) | ALLOWED | ALLOWED | ALLOWED | ALLOWED | ALLOWED | ALLOWED | ALLOWED | `sitemap.xml` | None |
| **Cloudflare** (`cloudflare.com`) | ALLOWED | ALLOWED | ALLOWED | ALLOWED | ALLOWED | ALLOWED | ALLOWED | `sitemap.xml` | Present |
| **Vercel** (`vercel.com`) | ALLOWED | ALLOWED | ALLOWED | ALLOWED | ALLOWED | ALLOWED | ALLOWED | `sitemap.xml` | Present |
| **The New York Times** (`nytimes.com`) | **ALLOWED** | **DISALLOWED** | **DISALLOWED** | **DISALLOWED** | **DISALLOWED** | **DISALLOWED** | **DISALLOWED** | 20+ `.xml.gz` sitemaps | None |
| **Reddit** (`reddit.com`) | **DISALLOWED** | **DISALLOWED** | **DISALLOWED** | **DISALLOWED** | **DISALLOWED** | **DISALLOWED** | **DISALLOWED** | None listed | None |
| **Medium** (`medium.com`) | ALLOWED | **DISALLOWED** | **DISALLOWED** | ALLOWED | ALLOWED | ALLOWED | ALLOWED | `sitemap.xml` | None |
| **IKEA** (`ikea.com`) | ALLOWED | ALLOWED | ALLOWED | ALLOWED | ALLOWED | ALLOWED | ALLOWED | `sitemap.xml` | None |
| **Linear** (`linear.app`) | ALLOWED | ALLOWED | ALLOWED | ALLOWED | ALLOWED | ALLOWED | ALLOWED | `sitemap.xml` | Present |
| **Basecamp** (`basecamp.com`) | ALLOWED | ALLOWED | ALLOWED | ALLOWED | ALLOWED | ALLOWED | ALLOWED | `sitemap.xml` | None |

### Key Empirical Observations

1. **The Selective Blocking Pattern (The NYTimes Case)**:
   The New York Times allows `*` (standard search engines like Googlebot and Bingbot crawl normally), but explicitly disallows all 9 AI crawler user-agents (`GPTBot`, `ClaudeBot`, `PerplexityBot`, `Google-Extended`, `OAI-SearchBot`, `ChatGPT-User`, `CCBot`, `Bytespider`, `Applebot-Extended`). A naive check inspecting only `User-agent: *` would falsely report NYTimes as 100% open to AI crawlers, missing the total discoverability block for answer engines.

2. **The Blanket Disallow Pattern (The Reddit Case)**:
   Reddit sets `User-agent: * Disallow: /` and replicates this block across every named AI bot, transitioning data access exclusively to contracted/authenticated API relationships.

3. **The Split-Policy Pattern (The Medium Case)**:
   Medium disallows `GPTBot`, `ClaudeBot`, `Bytespider`, and `Applebot-Extended`, while keeping `PerplexityBot`, `Google-Extended`, `OAI-SearchBot`, and `CCBot` allowed. This demonstrates that publishers increasingly maintain granular, divergent commercial policies across AI operators.

## Concrete Blindspots & Edge Cases for `crawl-and-render-audit`

1. **Gzipped Sitemaps (`.xml.gz`)**:
   - *Observed on*: `nytimes.com` (all 20+ sitemaps end in `.xml.gz`, such as `https://www.nytimes.com/sitemaps/new/news.xml.gz`).
   - *Failure Mode*: Standard XML parsers (`xml.etree.ElementTree.fromstring`) expecting raw XML text crash on gzipped binary streams if decompression is not performed before parsing.
   - *Impact*: Sitemap freshness checks report "Sitemap is referenced but not fetchable/parseable" as a false positive.

2. **WAF / Anti-Bot Security Challenge Walls vs True `noindex`**:
   - *Observed on*: `medium.com` (returns HTTP 403 Forbidden with Cloudflare Challenge containing `<meta name="robots" content="noindex, nofollow">`).
   - *Failure Mode*: If the crawler checks HTML meta tags on non-200 responses, it mistakes the WAF challenge page's `noindex` directive for an intentional application-level `noindex` on the underlying site.
   - *Remediation*: Only evaluate meta-robots and `X-Robots-Tag` on HTTP 200 responses; flag 403/503 responses under an access/challenge category.

3. **Custom Web Components / Non-standard SPA Shells**:
   - *Observed on*: `reddit.com` (serves `<shreddit-app>` custom elements where raw HTTP GET yields a 1-word body "Reddit" with status 200).
   - *Failure Mode*: Traditional SPA heuristics looking strictly for `<div id="root">` or `<div id="app">` miss modern custom element hydration wrappers (`<shreddit-app>`, `<lit-element>`, etc.), underestimating the render gap when headless rendering is inactive.

4. **Emergence of `/llms.txt`**:
   - *Observed on*: `stripe.com`, `cloudflare.com`, `vercel.com`, `linear.app`.
   - *Significance*: Forward-looking AI-discoverability signal. Checking for `/llms.txt` at the site root provides an immediate opportunity finding for site owners looking to provide canonical markdown entry points for LLMs.

## A note on ethics of the check itself

This list is used only to **read** what a site's own `robots.txt` says about
each agent (a static parse). It is never used to set an outgoing
`User-Agent` header in order to impersonate one of these crawlers and see if
a block is actually enforced server-side — that would be evading an access
control the site owner deliberately set, which is out of scope for a
recommend-only, read-only audit tool (see the guardrails in the brief).
