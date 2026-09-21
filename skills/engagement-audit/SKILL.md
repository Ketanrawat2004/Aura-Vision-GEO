---
name: engagement-audit
description: Audits on-site visitor retention across 8 core UX dimensions — orientation (What is this / Who is it for), value proposition clarity, actionable CTAs, navigation findability, context retention and breadcrumbs on deep routes, scannability and heading hierarchy, and dead-end detection.
license: MIT
allowed-tools: [bash, http_fetch]
---

# On-Site Engagement & Retention Audit

## When to use
Called by `audit-orchestrator`. Evaluates "why visitors who do arrive don't stay" — the on-site engagement half of the Adobe Hackathon Round 3 challenge.

## Inputs
- Shared page set from the orchestrator (URL, status, headers, HTML, visible text, links).

## Procedure (deterministic across 8 dimensions)

1. **What is this? (Orientation)**:
   - Verify presence of a prominent, descriptive `<h1>` on the homepage and landing routes.
   - Detect abstract slogans (e.g. "The Future is Now") that fail to explain the product category or service.

2. **Who is it for? (Audience Clarity)**:
   - Inspect opening content for target persona cues ("for developers", "built for teams", "for enterprise").

3. **Value Proposition**:
   - Detect whether the primary benefit statement is accessible within the first 300 words without excessive scrolling.

4. **Next Action (CTA Quality)**:
   - Identify actionable calls-to-action ("Start Free Trial", "Book Demo", "Explore Docs").
   - Flag complete absence of next steps or reliance on vague link text ("click here", "read more").

5. **Navigation Findability**:
   - Verify presence of accessible navigation links to the 4 essential pillars: Products/Services, Pricing, Contact/Support, and About/Company.

6. **Context Retention & Breadcrumbs**:
   - On deep subpages (2+ path segments), check whether brand identity, parent section context, and breadcrumbs are preserved for visitors arriving from direct AI search links.

7. **Scannability & Information Hierarchy**:
   - Detect dense walls of text (>140 words per paragraph) and pages lacking `<h2>` subheadings to structure long prose.

8. **Dead Ends**:
   - Flag public subpages lacking forward action links or global navigation.

## Output
`{"findings": [...], "opportunities": [...]}` under `category: "engagement"`.
