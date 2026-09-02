# Engagement severity calibration

Engagement defects are rarely "blocking" the way a robots.txt disallow is —
a confusing page doesn't make content disappear, it makes a visitor leave.
That's why almost every check in this skill tops out at `degrading`, not
`blocking`; reserve `blocking` in this category for something that actually
prevents the visitor from completing a primary action at all (a broken
"Buy"/"Sign up" button, a form that can't submit), which most static checks
here can't directly confirm — flag those as `degrading`/high-priority
instead of overclaiming `blocking` without behavioral evidence.

## Avoiding false positives on scannability and CTA checks
These two checks are the softest signals in the whole marketplace (see
`check_engagement.py`) — a long paragraph or a single "Learn more" link
isn't inherently bad. Keep both at `cosmetic`/low priority unless they're
paired with something that makes them actually costly (e.g. the *only* CTA
on a pricing page is unlabeled). Over-flagging subjective style choices is
exactly the kind of false positive the rubric penalizes — when in doubt on
these two checks specifically, don't emit a finding at all.

## Empirical Evidence from 10 Real-World Audited Sites

Testing across 10 live sites highlighted several recurring on-site UX, orientation, and navigation patterns:

| Site / Page | Above-the-Fold Orientation | Navigation & Structure | Conversion / CTA Clarity | Observed UX / Extraction Friction |
|---|---|---|---|---|
| **Basecamp** (`/`) | Preceded by cookie banner: *"We’d like to use cookies..."* | Clear `<nav>` on homepage; missing `<nav>` tag on `/pricing` (uses header `<div>`) | Clear: *"Sign up free"*, *"Start free trial"* | Cookie consent text occupies the first 35 words of DOM body, interfering with heuristic orientation text extraction. |
| **Linear** (`/`) | Hero headline: *"The product development system for teams and agents"* | Semantic `<nav>` with clear descriptive links | Clear: *"Sign up"*, *"Contact Docs"* | High aesthetic dark-mode layout with canvas background; keyboard navigation discovery relies on tooltips. |
| **Stripe** (`/pricing`) | Immediate fee overview and calculator | Semantic `<nav>` with mega-menu dropdowns | Multi-CTA: *"Start now"*, *"Contact sales"*, *"Chat now with sales"* | 88 sub-product sections make full vertical scanning arduous without sticky jump-links. |
| **Cloudflare** (`/plans/`) | Headline: *"Scale predictably — Pay only for what you use"* | Semantic `<nav>` with emergency *"Under attack?"* CTA | High clarity: *"Start building"*, *"Contact sales"* | Multi-currency and multi-tiered feature comparison table requires high cognitive load to digest. |
| **The New York Times** (`/`) | News headlines and breaking banners | Semantic `<nav>` with deep topical sections | Conversion CTA: *"Subscribe for $1/week"* | Dynamic subscriber paywall meter overlays and modal dimmers interrupt non-subscriber reading flow. |
| **Reddit** (`/`) | Dynamic feed of community posts | Client-side navigation inside `<shreddit-app>` | Generic CTA: *"Log In"*, *"Get App"* | Intrusive login prompts and app-install interstitials on mobile viewports. |

## Concrete Blindspots & Edge Cases for `engagement-audit`

1. **Cookie Consent Banners Polluting Above-the-Fold Orientation**:
   - *Observed on*: `basecamp.com`, `basecamp.com/pricing`, `ikea.com`.
   - *Mechanism*: Cookie consent banners (OneTrust, Cookiebot, custom dialogs) are frequently rendered as the first DOM elements directly inside `<body>`.
   - *Impact*: Static orientation checks extracting the first 150 words of body text analyze the cookie disclaimer ("We use cookies...") instead of the actual company headline and value proposition.
   - *Remediation*: Ignore elements with classes/IDs matching `cookie|consent|banner|modal|dialog` when extracting top-of-page orientation text.

2. **Header `<div>` Containers vs. Semantic `<nav>` Elements**:
   - *Observed on*: `basecamp.com/pricing`.
   - *Mechanism*: Single-purpose conversion/pricing pages often streamline navigation into simple header `<div>` containers rather than full semantic `<nav>` elements to reduce visual clutter.
   - *Severity Calibration*: Flag missing `<nav>` on subpages as `cosmetic/single-page` rather than `degrading/sitewide` if the homepage contains valid semantic navigation.

3. **Gating / Modal Interstitials (Regwalls & Paywalls)**:
   - *Observed on*: `nytimes.com`, `medium.com`, `reddit.com`.
   - *Mechanism*: Sites that allow initial page viewing but dynamically inject modal overlays or paywall banners degrade visitor retention and create dead ends for users arriving via answer-engine deep links.
