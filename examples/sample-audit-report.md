# AI Visibility Audit — 127.0.0.1:8931

Audited at 2026-09-02T05:17:44Z

**14 findings** — 0 critical, 7 high, 6 medium, 1 low

## [HIGH] F-001: robots.txt blocks known AI/answer-engine crawlers: GPTBot
*Category: discoverability · Confidence: high*

**Evidence:** can_fetch() returned False for ['GPTBot'] against http://127.0.0.1:8931/ per http://127.0.0.1:8931/robots.txt

**Fix (high priority):** Remove or narrow the Disallow rules for these agents unless the block is intentional (e.g. paywalled/private content).
> Why: A blocked crawler can't fetch the page at all — this isn't a ranking penalty, the content is architecturally invisible to that system regardless of quality.

## [HIGH] F-002: Sitemap lastmod dates are stale sitewide
*Category: discoverability · Confidence: high*

**Evidence:** Newest <lastmod> across 2 URLs is 2023-02-01 (1309 days old).

**Fix (medium priority):** Regenerate the sitemap so lastmod reflects real content changes.

## [HIGH] F-003: 1 public page(s) are marked noindex
*Category: discoverability · Confidence: high*

**Evidence:** noindex detected on: ['http://127.0.0.1:8931/pricing']

**Fix (high priority):** Remove noindex from pages meant to be publicly discoverable.

## [HIGH] F-004: Rendered content is 40.0x larger than raw HTML at http://127.0.0.1:8931/app/
*Category: discoverability · Confidence: high*

**Evidence:** Raw GET: 1 words. Headless render: 40 words.

**Fix (high priority):** Server-render or prerender this route so key content ships in the initial HTML response.
> Why: Fetchers that don't execute JavaScript — most AI-answer-engine crawlers included — only ever see the raw response. If the facts only exist after render, they don't exist for those systems.

## [HIGH] F-005: No <nav> element found
*Category: engagement · Confidence: medium*

**Evidence:** No <nav> tag in http://127.0.0.1:8931/.; No <nav> tag in http://127.0.0.1:8931/product/.

**Fix (medium priority):** Wrap primary navigation in a <nav> element with descriptive link text.

## [HIGH] F-006: No mobile viewport meta tag
*Category: engagement · Confidence: high*

**Evidence:** No <meta name="viewport"> found on http://127.0.0.1:8931/.; No <meta name="viewport"> found on http://127.0.0.1:8931/product/.

**Fix (medium priority):** Add <meta name="viewport" content="width=device-width, initial-scale=1">.

## [HIGH] F-007: No contact/about link found
*Category: engagement · Confidence: medium*

**Evidence:** No link containing 'contact' or 'about' found on http://127.0.0.1:8931/.; No link containing 'contact' or 'about' found on http://127.0.0.1:8931/product/.

**Fix (medium priority):** Add a visible link to a contact or about page from primary navigation.

## [MEDIUM] F-008: Page implies FAQPage content but has no FAQPage structured data
*Category: discoverability · Confidence: medium*

**Evidence:** Content-based signal detected for FAQPage (e.g. price pattern or FAQ-shaped headings) but @type=FAQPage absent from JSON-LD on http://127.0.0.1:8931/product/. Types actually present: ['Organization'].; Content-based signal detected for Product (e.g. price pattern or FAQ-shaped headings) but @type=Product absent from JSON-LD on http://127.0.0.1:8931/product/. Types actually present: ['Organization'].

**Fix (high priority):** Add FAQPage JSON-LD matching what the page already says in prose.
> Why: Structured data is what an assistant quotes from directly; prose alone requires the extractor to correctly parse free text, which is far less reliable.

## [MEDIUM] F-009: Organization structured data is present but missing required properties
*Category: discoverability · Confidence: high*

**Evidence:** Organization node missing name/url: {"@context": "https://schema.org", "@type": "Organization", "name": "Acme"}

**Fix (medium priority):** Fill in the missing required Organization properties.

## [MEDIUM] F-010: 1 image(s) likely carrying facts have no alt text
*Category: discoverability · Confidence: low*

**Evidence:** Images with no alt text and filenames suggesting factual content: ['/images/price-chart.png']

**Fix (medium priority):** Add descriptive alt text (or a plain-text equivalent nearby) restating the key facts the image carries.

## [MEDIUM] F-011: Key facts appear to live only inside a linked PDF
*Category: discoverability · Confidence: medium*

**Evidence:** PDF links whose href/anchor text suggest primary facts live there, with no on-page text equivalent found: ['/docs/pricing-sheet.pdf']

**Fix (high priority):** Mirror the PDF's key facts as plain HTML text on the page itself; keep the PDF as a download option, not the only copy.
> Why: Most fetchers extract page text directly; a fact that requires opening and parsing a separate PDF is far less likely to be read and used at all.

## [MEDIUM] F-012: Evergreen-sounding claims on a page whose newest date signal is 1326 days old
*Category: discoverability · Confidence: medium*

**Evidence:** http://127.0.0.1:8931/about/: phrasing matched an evergreen-claim pattern (e.g. 'currently', 'we are') with no 'as of' qualifier nearby; newest date signal found on the page is 2023-01-15 (1326 days old).

**Fix (medium priority):** Either refresh the content and its date, or add an explicit 'as of <date>' qualifier so the claim doesn't read as current when it may not be.
> Why: Assistants weight recency when deciding what to trust and repeat; an undated evergreen claim next to old date signals reads as unreliable once cross-checked.

## [MEDIUM] F-013: 1 internal link(s) lead to dead ends
*Category: engagement · Confidence: high*

**Evidence:** Broken internal links: [('http://127.0.0.1:8931/docs/pricing-sheet.pdf', 404)]

**Fix (medium priority):** Fix or remove these internal links.

## [LOW] F-014: Page has 2 <h1> elements
*Category: discoverability · Confidence: high*

**Evidence:** 2 <h1> elements found in raw HTML.

**Fix (low priority):** Reduce to a single <h1>; demote the rest to <h2>+.
