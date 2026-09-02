# AuraVision GEO Audit  https://www.amazon.in/

Audited at 2026-09-02T13:52:47Z

**6 findings**  1 critical, 1 high, 2 medium, 2 low

## [CRITICAL] F-001: robots.txt blocks known AI/answer-engine crawlers: GPTBot, OAI-SearchBot, ChatGPT-User, ClaudeBot, Claude-Web, PerplexityBot, Google-Extended, CCBot, Bytespider
*Category: discoverability  Confidence: high*

**Evidence:** can_fetch() returned False for ['GPTBot', 'OAI-SearchBot', 'ChatGPT-User', 'ClaudeBot', 'Claude-Web', 'PerplexityBot', 'Google-Extended', 'CCBot', 'Bytespider'] against https://www.amazon.in/ per https://www.amazon.in/robots.txt

**Fix (critical priority):** Remove or narrow the Disallow rules for these agents unless the block is intentional (e.g. paywalled/private content).
> Why: A blocked crawler can't fetch the page at all  this isn't a ranking penalty, the content is architecturally invisible to that system regardless of quality.

## [HIGH] F-002: No mobile viewport meta tag
*Category: engagement  Confidence: high*

**Evidence:** No <meta name="viewport"> found on https://www.amazon.in/.

**Fix (medium priority):** Add <meta name="viewport" content="width=device-width, initial-scale=1">.

## [MEDIUM] F-003: Page implies Product content but has no Product structured data
*Category: discoverability  Confidence: medium*

**Evidence:** Content-based signal detected for Product (e.g. price pattern or FAQ-shaped headings) but @type=Product absent from JSON-LD on https://www.amazon.in/. Types actually present: none.

**Fix (high priority):** Add Product JSON-LD matching what the page already says in prose.
> Why: Structured data is what an assistant quotes from directly; prose alone requires the extractor to correctly parse free text, which is far less reliable.

## [MEDIUM] F-004: 1 internal link(s) lead to dead ends
*Category: engagement  Confidence: high*

**Evidence:** Broken internal links: [('https://www.amazon.in/gp/site-directory?ref_=nav_em_js_disabled', 404)]

**Fix (medium priority):** Fix or remove these internal links.

## [LOW] F-005: Page has no <h1>
*Category: discoverability  Confidence: high*

**Evidence:** 0 <h1> elements found in raw HTML.

**Fix (low priority):** Add a single, descriptive <h1>.

## [LOW] F-006: Long, unbroken paragraphs
*Category: engagement  Confidence: low*

**Evidence:** https://www.amazon.in/: average 1118 words/paragraph across 1 paragraphs; longest is 1118 words.

**Fix (low priority):** Break long paragraphs up with subheadings, bullets, or shorter grafs.

## Beyond-defect opportunities
- **robots.txt doesn't reference a sitemap**  Add 'Sitemap: https://.../sitemap.xml' to robots.txt.
- **Publish an llms.txt at the site root**  Add /llms.txt pointing AI agents at your canonical markdown entry point.