#!/usr/bin/env python3
"""
Merge and synthesize raw findings from worker skills into the final audit report.
Standard library only (json, re, hashlib, datetime).

Guarantees:
  1. Strict adherence to Adobe Hackathon Round 3 Report Schema:
     - site, audited_at, summary (total_findings, critical, high, medium, low)
     - findings with: id, title, severity, evidence, suggested_action (summary, priority)
  2. Mathematical severity derivation (Impact x Scope).
  3. Semantic deduplication across worker skills via Jaccard title token similarity.
  4. Structured Markdown rendering for executive review.

Usage:
    python aggregate_report.py --site example.com \
        --inputs crawl.json render.json struct.json trust.json freshness.json engage.json \
        --out audit_report
"""
import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

SEVERITY_MATRIX = {
    ("blocking", "sitewide"): "critical",
    ("blocking", "section"): "high",
    ("blocking", "single-page"): "high",
    ("degrading", "sitewide"): "high",
    ("degrading", "section"): "medium",
    ("degrading", "single-page"): "medium",
    ("cosmetic", "sitewide"): "medium",
    ("cosmetic", "section"): "low",
    ("cosmetic", "single-page"): "low",
}

SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}

STOPWORDS = {
    "a", "an", "the", "on", "of", "no", "for", "to", "and", "is", "are", "not",
    "has", "have", "page", "pages", "site", "found", "detected", "in", "at", "with"
}


def normalize_title(title: str) -> set:
    words = re.findall(r"[a-z0-9]+", title.lower())
    stemmed = (w[:-1] if w.endswith("s") and len(w) > 3 else w for w in words)
    return {w for w in stemmed if w not in STOPWORDS}


def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def derive_severity(finding: dict) -> str:
    """Derives severity strictly from impact and scope per the orchestrator severity matrix."""
    impact = finding.get("impact", "degrading")
    scope = finding.get("scope", "section")
    return SEVERITY_MATRIX.get((impact, scope), "medium")


def classify_access_failure(status_code: int, error_str: str, site_url: str) -> dict:
    """
    Distinguishes the exact cause when zero pages could be accessed,
    producing an evidence-based audit coverage limitation finding
    with accurate severity derived from the severity matrix and confidence.
    """
    err_lower = str(error_str).lower()

    # 1. robots.txt restriction (site's own deliberate access policy)
    if "robots.txt" in err_lower or (status_code == 403 and "robots.txt" in err_lower):
        cause = "robots.txt restriction"
        title = "Audit coverage limited: Automated crawler restricted by robots.txt"
        evidence = f"Initial crawl to {site_url} was halted because robots.txt disallows automated crawler user-agents ({error_str})."
        action_summary = "Review robots.txt directives if you wish to permit AI answer engine crawlers (e.g. GPTBot, ClaudeBot, PerplexityBot) to index public routes."
        mechanism = "Answer engines inspect robots.txt before crawling; if all crawlers or specific AI agents are disallowed, they skip indexing the domain."
        impact = "blocking"
        scope = "sitewide"
        confidence = "high"

    # 2. HTTP/access restriction - 401 Unauthorized (site's own deliberate access policy)
    elif status_code == 401 or "unauthorized" in err_lower:
        cause = "HTTP/access restriction"
        title = "Audit coverage limited: Target route requires authentication (HTTP 401)"
        evidence = f"Request to {site_url} returned HTTP 401 Unauthorized ({error_str}). The read-only audit tool operates without user credentials."
        action_summary = "Verify whether this route is intended to be public. Public informational content intended for AI discovery should not require user login."
        mechanism = "Automated answer engine crawlers operate without user session credentials and cannot access authenticated routes."
        impact = "blocking"
        scope = "sitewide"
        confidence = "high"

    # 3. HTTP/access restriction - 403 Forbidden (site's own deliberate access policy)
    elif status_code == 403 or "forbidden" in err_lower:
        cause = "HTTP/access restriction"
        title = "Audit coverage limited: Route returned HTTP 403 Forbidden"
        evidence = f"Initial request to {site_url} was declined by the server or CDN firewall (HTTP 403: {error_str})."
        action_summary = "Check web server, WAF, or CDN access policies to confirm whether automated AI retrieval bots are permitted."
        mechanism = "WAF challenge walls or 403 responses prevent search bots and AI answer engines from reading HTML content."
        impact = "blocking"
        scope = "sitewide"
        confidence = "high"

    # 4. HTTP/access restriction - 429 Rate-Limited (defensive/temporary)
    elif status_code == 429 or "too many requests" in err_lower:
        cause = "HTTP/access restriction"
        title = "Audit coverage limited: Target route rate-limited requests (HTTP 429)"
        evidence = f"Initial request to {site_url} returned HTTP 429 Too Many Requests ({error_str})."
        action_summary = "Review server rate-limiting rules for automated scrapers and answer-engine bots."
        mechanism = "Rate-limiting automated requests on the root route prevents answer engines from indexing the domain."
        impact = "degrading"
        scope = "sitewide"
        confidence = "high"

    # 5. Target website unavailable (HTTP 5xx or 404 - site down or broken)
    elif status_code >= 500 or status_code == 404 or any(k in err_lower for k in ("service unavailable", "bad gateway", "gateway timeout", "not found")):
        cause = "target website unavailable"
        title = f"Audit coverage limited: Target website returned HTTP {status_code}"
        evidence = f"Target server responded with HTTP {status_code} ({error_str}) when fetching {site_url}."
        action_summary = f"Inspect server availability and HTTP {status_code} error responses on this URL."
        mechanism = "HTTP server errors prevent search engines and AI assistants from accessing content."
        impact = "blocking"
        scope = "sitewide"
        confidence = "high"

    # 6. Timeout (ambiguous: network conditions vs server load)
    elif any(k in err_lower for k in ("timed out", "timeout")):
        cause = "timeout"
        title = "Audit coverage limited: Request timed out reaching target URL"
        evidence = (
            f"Request to {site_url} timed out ({error_str}). The server did not respond within the allocated timeout window. "
            "Note: This failure may reflect audit environment network conditions or temporary latency rather than an intrinsic website defect."
        )
        action_summary = "Verify server responsiveness, network latency, and firewall response times."
        mechanism = "Slow response times or dropped packets cause automated crawlers to abort fetches."
        impact = "blocking"
        scope = "sitewide"
        confidence = "low"

    # 7. DNS/network failure in audit environment (ambiguous: local resolver vs invalid host)
    elif status_code == 0 and any(k in err_lower for k in ("getaddrinfo", "nodename", "name or service not known", "connection refused", "network is unreachable", "no route to host", "10061", "10060", "11001", "winerror", "errno 111", "name resolution")):
        cause = "DNS/network failure in audit environment"
        title = "Audit coverage limited: Host could not be reached from audit environment"
        evidence = (
            f"Network connection or DNS resolution to {site_url} failed ({error_str}). "
            "Note: This failure may reflect local network, DNS resolver, or firewall limits in the audit environment rather than an intrinsic defect of the target website."
        )
        action_summary = "Confirm target URL syntax, check audit environment internet connectivity, and verify domain DNS records are globally propagated."
        mechanism = "When DNS resolution or local socket connection fails, the crawler cannot connect to evaluate the page."
        impact = "blocking"
        scope = "sitewide"
        confidence = "low"

    # 8. Unsupported content (ambiguous: non-HTML payload vs endpoint type)
    elif any(k in err_lower for k in ("content-type", "expected text/html", "blank html", "0 bytes", "empty")):
        cause = "unsupported content"
        title = "Audit coverage limited: Target returned non-HTML or empty content"
        evidence = (
            f"Target returned non-HTML or empty payload ({error_str}) at {site_url}. Aura-Vision-GEO audits HTML web pages. "
            "Note: This failure may reflect crawler header negotiation or payload routing rather than an intrinsic defect of the target website."
        )
        action_summary = "Ensure the target URL serves text/html content."
        mechanism = "GEO auditing evaluates DOM and HTML markup; binary or non-HTML streams cannot be parsed as web pages."
        impact = "blocking"
        scope = "sitewide"
        confidence = "low"

    # 9. Crawler failure / generic (ambiguous)
    else:
        cause = "crawler failure"
        title = "Audit coverage limited: Automated crawler could not retrieve valid HTML"
        evidence = (
            f"Crawler could not retrieve valid HTML pages from {site_url} ({error_str}). "
            "Note: This failure may reflect audit runner fetch constraints rather than an intrinsic defect of the target website."
        )
        action_summary = "Verify URL accessibility and crawler permissions."
        mechanism = "Audits require accessible HTML pages to evaluate discoverability and retention."
        impact = "blocking"
        scope = "sitewide"
        confidence = "low"

    raw_finding = {"impact": impact, "scope": scope}
    severity = derive_severity(raw_finding)

    return {
        "cause": cause,
        "finding": {
            "id": "F-001",
            "title": title,
            "severity": severity,
            "impact": impact,
            "scope": scope,
            "category": "discoverability",
            "subcategory": "crawlability",
            "confidence": confidence,
            "evidence": evidence,
            "suggested_action": {
                "summary": action_summary,
                "priority": severity,
                "mechanism": mechanism
            }
        }
    }


def load_worker_outputs(paths: list) -> tuple:
    findings, opportunities = [], []
    empirical = None
    for p in paths:
        if not p:
            continue
        try:
            with open(p, encoding="utf-8") as f:
                data = json.load(f)
            findings.extend(data.get("findings", []))
            opportunities.extend(data.get("opportunities", []))
            if "empirical_corroboration" in data and not empirical:
                empirical = data["empirical_corroboration"]
        except Exception as e:
            print(f"warning: error loading worker output {p}: {e}", file=sys.stderr)
    return findings, opportunities, empirical


def dedupe(findings: list, similarity_threshold: float = 0.4) -> list:
    """Merges findings sharing similar scope and high token overlap."""
    merged = []
    used = [False] * len(findings)

    for i, f in enumerate(findings):
        if used[i]:
            continue
        group = [f]
        used[i] = True
        f_tokens = normalize_title(f.get("title", ""))

        for j in range(i + 1, len(findings)):
            if used[j]:
                continue
            g = findings[j]
            # Match subcategory or category
            cat_match = g.get("subcategory") == f.get("subcategory") or g.get("category") == f.get("category")
            if cat_match and jaccard(f_tokens, normalize_title(g.get("title", ""))) >= similarity_threshold:
                group.append(g)
                used[j] = True

        if len(group) == 1:
            merged.append(f)
        else:
            best = max(group, key=lambda x: len(x.get("title", "")))
            best = dict(best)
            
            # Extract per-item URL attribution
            affected_urls = []
            page_evidences = []
            for g in group:
                u = g.get("url")
                if not u:
                    m = re.search(r'https?://[^\s,;"\'\)]+', g.get("title", "") + " " + g.get("evidence", ""))
                    if m:
                        u = m.group(0)
                if u and u not in affected_urls:
                    affected_urls.append(u)
                ev = g.get("evidence", "").strip()
                if ev:
                    page_evidences.append((u, ev))

            if affected_urls and any(u for u, _ in page_evidences):
                best["affected_urls"] = affected_urls
                per_url_items = []
                seen = set()
                for u, ev in page_evidences:
                    key = (u, ev)
                    if key in seen:
                        continue
                    seen.add(key)
                    if u and not ev.startswith("http") and not ev.startswith(u):
                        per_url_items.append(f"{u}: {ev}")
                    else:
                        per_url_items.append(ev)
                best["evidence"] = f"Found on {len(group)} pages — " + "; ".join(per_url_items)
            else:
                unique_evs = list(dict.fromkeys(ev for _, ev in page_evidences))
                best["evidence"] = "; ".join(unique_evs)

            merged.append(best)

    return merged


def build_report(
    site: str,
    findings: list,
    opportunities: list = None,
    crawled_pages_count: int = 1,
    coverage: dict = None,
    empirical_corroboration: dict = None
) -> dict:
    opportunities = opportunities or []

    for f in findings:
        f["severity"] = derive_severity(f)

    # Sort strictly by severity rank (critical -> high -> medium -> low), then confidence
    findings.sort(key=lambda f: (
        SEVERITY_RANK.get(f["severity"], 4),
        0 if f.get("confidence") == "high" else 1,
        f.get("category", "")
    ))

    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    out_findings = []

    for idx, f in enumerate(findings, start=1):
        sev = f["severity"]
        counts[sev] = counts.get(sev, 0) + 1
        
        # Ensure suggested_action is a dict with summary and priority
        act = f.get("suggested_action", {})
        if isinstance(act, str):
            act = {"summary": act, "priority": sev}
        elif isinstance(act, dict):
            if "summary" not in act:
                act["summary"] = "Remediate this finding per best practices."
            if "priority" not in act:
                act["priority"] = sev

        clean_finding = {
            "id": f"F-{idx:03d}",
            "title": f["title"],
            "severity": sev,
            "category": f.get("category", "discoverability"),
            "subcategory": f.get("subcategory", f.get("category", "discoverability")),
            "confidence": f.get("confidence", "high"),
            "evidence": f["evidence"],
            "suggested_action": {
                "summary": act["summary"],
                "priority": act.get("priority", sev)
            }
        }
        if f.get("affected_urls"):
            clean_finding["affected_urls"] = f["affected_urls"]
        elif f.get("url"):
            clean_finding["affected_urls"] = [f["url"]]
        if act.get("mechanism"):
            clean_finding["suggested_action"]["mechanism"] = act["mechanism"]

        out_findings.append(clean_finding)

    out_opportunities = []
    for o in opportunities:
        act = o.get("suggested_action", {})
        if isinstance(act, str):
            act = {"summary": act, "priority": "low"}
        out_opportunities.append({
            "title": o["title"],
            "suggested_action": {
                "summary": act.get("summary", "Proactive improvement."),
                "priority": act.get("priority", "low")
            }
        })

    if (coverage and coverage.get("status") == "not_accessible") or crawled_pages_count == 0:
        score = None
        grade = None
    else:
        crit = counts["critical"]
        high = counts["high"]
        med = counts["medium"]
        # In partial crawl or normal crawl: exclude coverage limitation findings from penalizing the site score
        non_coverage_low = sum(
            1 for f in out_findings
            if f.get("severity") == "low" and not (f.get("subcategory") == "crawlability" and "coverage" in f.get("title", "").lower())
        )
        score = max(10, min(100, 100 - (crit * 30 + high * 15 + med * 6 + non_coverage_low * 2)))
        if score >= 90: grade = "A+"
        elif score >= 80: grade = "A"
        elif score >= 70: grade = "B"
        elif score >= 60: grade = "C"
        elif score >= 50: grade = "D"
        else: grade = "F"

    audited_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    res = {
        "site": site,
        "audited_at": audited_at,
        "crawled_pages": crawled_pages_count,
        "score": score,
        "grade": grade,
        "summary": {
            "total_findings": len(out_findings),
            "critical": counts["critical"],
            "high": counts["high"],
            "medium": counts["medium"],
            "low": counts["low"]
        },
        "findings": out_findings,
        "opportunities": out_opportunities
    }
    if empirical_corroboration:
        res["empirical_corroboration"] = empirical_corroboration
    else:
        res["empirical_corroboration"] = {
            "status": "not_run",
            "reason": "Empirical search verification is optional and was not enabled. Provide --empirical or set an API key (BRAVE_API_KEY, TAVILY_API_KEY, SERPAPI_API_KEY) for live external validation."
        }
    if coverage:
        res["coverage"] = coverage
    return res


def render_markdown(report: dict) -> str:
    s = report["summary"]
    score = report.get("score")
    grade = report.get("grade")
    grade_str = f" | **GEO Health Score:** `{score}/100 (Grade {grade})`" if score is not None else " | **GEO Health Score:** `Not Assessed (Zero Pages Accessible)`"
    lines = [
        f"# AuraVision GEO Audit Report — {report['site']}",
        "",
        f"**Audited at:** `{report['audited_at']}` | **Pages Crawled:** `{report.get('crawled_pages', 1)}`{grade_str}",
        "",
        f"### Executive Summary",
        f"- **Total Findings:** `{s['total_findings']}`",
        f"- **Critical:** `{s['critical']}` | **High:** `{s['high']}` | **Medium:** `{s['medium']}` | **Low:** `{s['low']}`",
        "",
    ]

    if report.get("coverage"):
        cov = report["coverage"]
        c_status = cov.get("status", "verified").upper()
        lines.extend([
            f"### Coverage & Accessibility Audit",
            f"- **Crawl Status:** `{c_status}`",
            f"- **Accessible Pages Evaluated:** `{cov.get('accessible_pages', 0)}`",
            f"- **Inaccessible / Restricted Routes:** `{cov.get('inaccessible_routes', 0)}`",
        ])
        if cov.get("reason"):
            lines.append(f"- **Coverage Note:** {cov['reason']}")
        if cov.get("verified"):
            lines.append(f"- **Verified Dimensions:** {', '.join(cov['verified'])}")
        if cov.get("not_verified"):
            lines.append(f"- **Not Verified (Access Limits):** {', '.join(cov['not_verified'])}")
        lines.append("")

    if report.get("empirical_corroboration"):
        emp = report["empirical_corroboration"]
        e_status = emp.get("status", "not_run").upper()
        lines.extend([
            f"### Empirical External Grounding",
            f"- **Validation Status:** `{e_status}`",
        ])
        if emp.get("provider"):
            lines.append(f"- **Search Provider:** `{emp['provider']}`")
        if emp.get("query"):
            lines.append(f"- **Query Executed:** `{emp['query']}`")
        if emp.get("status") == "completed":
            matched_str = "CONFIRMED (Domain present in search results)" if emp.get("matched") else "UNVERIFIED (Domain absent from search results)"
            lines.append(f"- **Domain Presence:** `{matched_str}`")
        if emp.get("evidence"):
            lines.append(f"- **Evidence:** {emp['evidence']}")
        if emp.get("reason"):
            lines.append(f"- **Status Detail:** {emp['reason']}")
        lines.append("")

    lines.extend([
        "---",
        "",
        "## Diagnostic Findings",
        ""
    ])

    if not report["findings"]:
        lines.append("No defects detected. Website demonstrates clean AI-discoverability and on-site engagement structure.")
        lines.append("")

    for f in report["findings"]:
        badge = f"[{f['severity'].upper()}]"
        lines.append(f"### {badge} {f['id']}: {f['title']}")
        lines.append(f"- **Category:** `{f.get('category')}` / `{f.get('subcategory')}` (Confidence: `{f.get('confidence')}`)")
        lines.append(f"- **Evidence:** {f['evidence']}")
        if f.get("affected_urls") and len(f["affected_urls"]) > 1:
            urls_fmt = ", ".join(f"`{u}`" for u in f["affected_urls"][:4])
            if len(f["affected_urls"]) > 4:
                urls_fmt += f" (and {len(f['affected_urls']) - 4} more)"
            lines.append(f"- **Affected Routes ({len(f['affected_urls'])}):** {urls_fmt}")
        action = f["suggested_action"]
        lines.append(f"- **Action ({action.get('priority', 'medium')} priority):** {action['summary']}")
        if action.get("mechanism"):
            lines.append(f"  > **Why this matters:** {action['mechanism']}")
        if action.get("fix_snippet"):
            lines.append(f"  ```\n  {action['fix_snippet']}\n  ```")
        lines.append("")

    if report.get("opportunities"):
        lines.append("---")
        lines.append("## Proactive Beyond-Defect Recommendations")
        lines.append("")
        for o in report["opportunities"]:
            lines.append(f"- **{o['title']}**: {o['suggested_action']['summary']}")
            if o.get("suggested_action", {}).get("fix_snippet"):
                lines.append(f"  ```\n  {o['suggested_action']['fix_snippet']}\n  ```")
        lines.append("")

    return "\n".join(lines)


def html_escape(s: str) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def render_html(report: dict) -> str:
    s = report["summary"]
    site = html_escape(report["site"])
    audited_at = html_escape(report["audited_at"])
    crawled = report.get("crawled_pages", 1)

    findings_html = []
    if not report["findings"]:
        findings_html.append('<div class="empty-state">No defects detected. Website demonstrates clean AI-discoverability and on-site engagement structure.</div>')
    else:
        for f in report["findings"]:
            fid = html_escape(f["id"])
            title = html_escape(f["title"])
            sev = f["severity"].lower()
            cat = html_escape(f.get("category", "general"))
            subcat = html_escape(f.get("subcategory", "general"))
            ev = html_escape(f.get("evidence", ""))
            act = f.get("suggested_action", {})
            act_sum = html_escape(act.get("summary", ""))
            act_prio = html_escape(act.get("priority", "medium"))
            act_mech = html_escape(act.get("mechanism", ""))
            fix_snip = act.get("fix_snippet", "")

            code_markup = ""
            if fix_snip:
                code_markup = f'''
                <div class="code-box">
                  <div class="code-title">
                    <span>Actionable Code Fix Implementation</span>
                    <button class="copy-btn" onclick="copySnippet(this)">Copy</button>
                  </div>
                  <pre><code>{html_escape(fix_snip)}</code></pre>
                </div>'''

            mech_markup = f'<div class="mech-box"><strong>Why this matters:</strong> {act_mech}</div>' if act_mech else ''

            pillar_label = f"Pillar: {cat}" if cat == subcat else f"Pillar: {cat} &bull; {subcat}"
            findings_html.append(f'''
            <div class="card sev-{sev}" data-sev="{sev}">
              <div class="card-top">
                <span class="badge badge-{sev}">{sev.upper()}</span>
                <span class="finding-id">{fid}</span>
                <h3 class="card-title">{title}</h3>
              </div>
              <div class="card-tags">
                <span class="pill">{pillar_label}</span>
                <span class="pill">Confidence: {html_escape(f.get("confidence", "high"))}</span>
              </div>
              <div class="evidence-block">
                <div class="evidence-label">Detected Evidence:</div>
                <div class="evidence-content">{ev}</div>
              </div>
              <div class="action-block">
                <div class="action-top">
                  <span class="prio prio-{act_prio}">{act_prio.upper()} PRIORITY</span>
                  <div class="action-sum">{act_sum}</div>
                </div>
                {mech_markup}
                {code_markup}
              </div>
            </div>''')

    opps_html = []
    for o in report.get("opportunities", []):
        o_title = html_escape(o.get("title", ""))
        o_sum = html_escape(o.get("suggested_action", {}).get("summary", ""))
        o_snip = o.get("suggested_action", {}).get("fix_snippet", "")
        code_part = f'''
        <div class="code-box" style="margin-top:8px;">
          <div class="code-title">
            <span>Example Format</span>
            <button class="copy-btn" onclick="copySnippet(this)">Copy</button>
          </div>
          <pre><code>{html_escape(o_snip)}</code></pre>
        </div>''' if o_snip else ''
        opps_html.append(f'''
        <li class="opp-item">
            <strong>{o_title}</strong>
            <p>{o_sum}</p>
            {code_part}
        </li>''')

    score = report.get("score")
    grade = report.get("grade")
    if score is None:
        score_disp = "N/A"
        grade_disp = "(Not Assessed)"
        score_col = "#94a3b8"
    else:
        score_disp = f"{score}/100"
        grade_disp = f"({grade})"
        score_col = "#10b981" if score >= 80 else ("#f59e0b" if score >= 60 else "#ef4444")
    cov_html = ""
    if report.get("coverage"):
        cov = report["coverage"]
        c_status = cov.get("status", "verified").upper()
        cov_col = "#10b981" if c_status == "VERIFIED" else ("#f59e0b" if c_status == "PARTIAL" else "#ef4444")
        v_str = ", ".join(cov.get("verified", [])) or "None"
        nv_str = ", ".join(cov.get("not_verified", [])) or "None"
        cov_html = f'''
        <div style="margin-top:16px; padding:12px 16px; background:#070a12; border:1px solid var(--border); border-radius:8px;">
          <div style="display:flex; align-items:center; gap:8px; margin-bottom:6px;">
            <span style="background:{cov_col}; color:#fff; font-size:11px; font-weight:700; padding:2px 8px; border-radius:4px;">COVERAGE: {c_status}</span>
            <span style="font-size:12px; color:var(--subtext);">{cov.get('accessible_pages', 0)} accessible / {cov.get('inaccessible_routes', 0)} restricted</span>
          </div>
          <div style="font-size:12px; color:#cbd5e1;"><strong>Verified Dimensions:</strong> {html_escape(v_str)}</div>
          <div style="font-size:12px; color:#f87171; margin-top:2px;"><strong>Not Verified (Access Restricted):</strong> {html_escape(nv_str)}</div>
        </div>'''

    emp_html = ""
    if report.get("empirical_corroboration"):
        emp = report["empirical_corroboration"]
        e_status = emp.get("status", "not_run").upper()
        if e_status == "COMPLETED":
            e_col = "#10b981" if emp.get("matched") else "#ef4444"
            e_lbl = "VERIFIED" if emp.get("matched") else "UNVERIFIED"
        elif e_status == "ERROR":
            e_col = "#ef4444"
            e_lbl = "ERROR"
        else:
            e_col = "#64748b"
            e_lbl = "NOT RUN"

        emp_ev = html_escape(emp.get("evidence") or emp.get("reason") or "Optional empirical check not executed.")
        emp_prov = f" &bull; Provider: {html_escape(emp.get('provider', 'N/A'))}" if emp.get("provider") else ""
        emp_q = f" &bull; Query: <code>{html_escape(emp.get('query', ''))}</code>" if emp.get("query") else ""
        emp_html = f'''
        <div style="margin-top:12px; padding:12px 16px; background:#070a12; border:1px solid var(--border); border-radius:8px;">
          <div style="display:flex; align-items:center; gap:8px; margin-bottom:6px;">
            <span style="background:{e_col}; color:#fff; font-size:11px; font-weight:700; padding:2px 8px; border-radius:4px;">EMPIRICAL GROUNDING: {e_lbl}</span>
            <span style="font-size:12px; color:var(--subtext);">{emp_prov}{emp_q}</span>
          </div>
          <div style="font-size:12px; color:#cbd5e1;">{emp_ev}</div>
        </div>'''

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AuraVision GEO Audit &mdash; {site}</title>
<style>
  :root {{
    --bg: #0b0f19;
    --card: #151d2e;
    --border: #243049;
    --text: #e2e8f0;
    --subtext: #94a3b8;
    --crit: #ef4444;
    --high: #f97316;
    --med: #eab308;
    --low: #38bdf8;
    --primary: #3b82f6;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: var(--bg); color: var(--text); padding: 32px 16px; line-height: 1.5; }}
  .container {{ max-width: 1080px; margin: 0 auto; }}
  header {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 24px; margin-bottom: 24px; }}
  .header-top {{ display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; margin-bottom: 16px; }}
  h1 {{ font-size: 24px; font-weight: 700; color: #fff; }}
  .site-badge {{ background: #1e293b; color: #38bdf8; padding: 4px 12px; border-radius: 6px; font-family: monospace; font-size: 14px; border: 1px solid #334155; }}
  .meta-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 12px; }}
  .stat-box {{ background: #0f172a; border: 1px solid var(--border); border-radius: 8px; padding: 12px; text-align: center; }}
  .stat-num {{ font-size: 22px; font-weight: 700; }}
  .stat-lbl {{ font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; color: var(--subtext); margin-top: 4px; }}
  .num-crit {{ color: var(--crit); }}
  .num-high {{ color: var(--high); }}
  .num-med {{ color: var(--med); }}
  .num-low {{ color: var(--low); }}
  .num-tot {{ color: #38bdf8; }}
  .num-pages {{ color: #a855f7; }}
  h2 {{ font-size: 18px; color: #fff; margin: 28px 0 16px; border-left: 4px solid var(--primary); padding-left: 10px; }}
  .filter-bar {{ display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin: 16px 0; }}
  .filter-lbl {{ font-size: 13px; color: var(--subtext); margin-right: 4px; }}
  .filter-btn {{ background: var(--card); border: 1px solid var(--border); color: var(--text); padding: 5px 12px; border-radius: 6px; font-size: 12px; cursor: pointer; transition: all 0.2s; }}
  .filter-btn:hover {{ border-color: var(--primary); color: #fff; }}
  .filter-btn.active {{ background: var(--primary); border-color: var(--primary); color: #fff; font-weight: 600; }}
  .card {{ background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 20px; margin-bottom: 16px; position: relative; transition: all 0.2s; }}
  .card.sev-critical {{ border-left: 4px solid var(--crit); }}
  .card.sev-high {{ border-left: 4px solid var(--high); }}
  .card.sev-medium {{ border-left: 4px solid var(--med); }}
  .card.sev-low {{ border-left: 4px solid var(--low); }}
  .card-top {{ display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 8px; }}
  .badge {{ font-size: 11px; font-weight: 700; padding: 3px 8px; border-radius: 4px; color: #fff; }}
  .badge-critical {{ background: var(--crit); }}
  .badge-high {{ background: var(--high); }}
  .badge-medium {{ background: var(--med); }}
  .badge-low {{ background: var(--low); }}
  .card-title {{ font-size: 16px; font-weight: 600; color: #fff; flex: 1; }}
  .pill {{ font-size: 11px; background: #1e293b; color: #cbd5e1; padding: 2px 8px; border-radius: 4px; border: 1px solid #334155; }}
  .evidence-block {{ background: #0b1120; border: 1px solid #1e293b; border-radius: 6px; padding: 12px; margin-bottom: 12px; }}
  .evidence-label {{ font-size: 11px; color: var(--subtext); text-transform: uppercase; margin-bottom: 4px; font-weight: 600; }}
  .evidence-content {{ font-family: monospace; font-size: 13px; color: #e2e8f0; word-break: break-all; }}
  .action-block {{ background: #131d33; border: 1px solid #23345a; border-radius: 6px; padding: 14px; }}
  .action-top {{ display: flex; align-items: center; gap: 10px; margin-bottom: 6px; flex-wrap: wrap; }}
  .prio {{ font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 3px; }}
  .prio-critical {{ background: #7f1d1d; color: #fca5a5; }}
  .prio-high {{ background: #7c2d12; color: #fdba74; }}
  .prio-medium {{ background: #713f12; color: #fde047; }}
  .prio-low {{ background: #1e3a8a; color: #93c5fd; }}
  .action-sum {{ font-weight: 600; color: #f1f5f9; font-size: 14px; }}
  .mech-box {{ font-size: 13px; color: #cbd5e1; margin-top: 6px; padding-left: 10px; border-left: 2px solid #6366f1; }}
  .code-box {{ margin-top: 12px; background: #070a12; border: 1px solid #1e293b; border-radius: 6px; overflow: hidden; }}
  .code-title {{ display: flex; justify-content: space-between; align-items: center; background: #0f172a; padding: 6px 12px; font-size: 11px; color: #94a3b8; border-bottom: 1px solid #1e293b; font-weight: 600; }}
  .copy-btn {{ background: #1e293b; border: 1px solid #334155; color: #38bdf8; font-size: 11px; padding: 2px 8px; border-radius: 4px; cursor: pointer; transition: all 0.2s; }}
  .copy-btn:hover {{ background: #334155; color: #fff; }}
  pre {{ padding: 12px; font-family: Consolas, Monaco, "Courier New", monospace; font-size: 12px; color: #38bdf8; overflow-x: auto; }}
  .opp-item {{ background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 14px; margin-bottom: 10px; list-style: none; }}
  .opp-item strong {{ color: #38bdf8; font-size: 14px; }}
  .opp-item p {{ font-size: 13px; color: var(--text); margin-top: 4px; }}
  footer {{ text-align: center; font-size: 12px; color: var(--subtext); margin-top: 40px; padding-top: 20px; border-top: 1px solid var(--border); }}
</style>
</head>
<body>
<div class="container">
  <header>
    <div class="header-top">
      <div>
        <h1>AuraVision GEO Audit Report</h1>
        <div style="font-size: 12px; color: var(--subtext); margin-top: 4px;">Audited at: {audited_at}</div>
      </div>
      <div class="site-badge">{site}</div>
    </div>
    <div class="meta-grid">
      <div class="stat-box"><div class="stat-num" style="color:{score_col};">{score_disp}</div><div class="stat-lbl">GEO Score {grade_disp}</div></div>
      <div class="stat-box"><div class="stat-num num-tot">{s['total_findings']}</div><div class="stat-lbl">Total Findings</div></div>
      <div class="stat-box"><div class="stat-num num-crit">{s['critical']}</div><div class="stat-lbl">Critical</div></div>
      <div class="stat-box"><div class="stat-num num-high">{s['high']}</div><div class="stat-lbl">High</div></div>
      <div class="stat-box"><div class="stat-num num-med">{s['medium']}</div><div class="stat-lbl">Medium</div></div>
      <div class="stat-box"><div class="stat-num num-low">{s['low']}</div><div class="stat-lbl">Low</div></div>
      <div class="stat-box"><div class="stat-num num-pages">{crawled}</div><div class="stat-lbl">Pages Crawled</div></div>
    </div>
    {cov_html}
    {emp_html}
  </header>

  <h2>Diagnostic Findings &amp; Recommended Fixes</h2>
  
  <div class="filter-bar">
    <span class="filter-lbl">Filter Findings:</span>
    <button class="filter-btn active" onclick="filterSev(this, 'all')">All ({s['total_findings']})</button>
    <button class="filter-btn" onclick="filterSev(this, 'critical')">Critical ({s['critical']})</button>
    <button class="filter-btn" onclick="filterSev(this, 'high')">High ({s['high']})</button>
    <button class="filter-btn" onclick="filterSev(this, 'medium')">Medium ({s['medium']})</button>
    <button class="filter-btn" onclick="filterSev(this, 'low')">Low ({s['low']})</button>
  </div>

  <div id="findings-container">
    {''.join(findings_html)}
  </div>

  {'<h2>Proactive Beyond-Defect Opportunities</h2><ul>' + ''.join(opps_html) + '</ul>' if opps_html else ''}

  <footer>
    AuraVision GEO &bull; Built to agentskills.io standard for Adobe University Hackathon 2026
  </footer>
</div>

<script>
function filterSev(btn, sev) {{
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  document.querySelectorAll('#findings-container .card').forEach(c => {{
    if (sev === 'all' || c.getAttribute('data-sev') === sev) {{
      c.style.display = 'block';
    }} else {{
      c.style.display = 'none';
    }}
  }});
}}

function copySnippet(btn) {{
  const code = btn.closest('.code-box').querySelector('code').innerText;
  navigator.clipboard.writeText(code).then(() => {{
    const orig = btn.innerText;
    btn.innerText = 'Copied!';
    btn.style.background = '#059669';
    btn.style.borderColor = '#059669';
    btn.style.color = '#fff';
    setTimeout(() => {{
      btn.innerText = orig;
      btn.style.background = '';
      btn.style.borderColor = '';
      btn.style.color = '';
    }}, 1800);
  }}).catch(() => {{
    btn.innerText = 'Failed';
  }});
}}
</script>
</body>
</html>'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True)
    ap.add_argument("--inputs", nargs="+", required=True, help="Worker-skill JSON output files")
    ap.add_argument("--out", default="audit_report", help="Output basename (no extension)")
    ap.add_argument("--pages-count", type=int, default=1, help="Total crawled pages count")
    ap.add_argument("--coverage-json", default=None, help="Path to coverage metadata JSON")
    ap.add_argument("--empirical-json", default=None, help="Path to empirical search JSON")
    args = ap.parse_args()
    if args.out:
        for ext in (".json", ".md", ".html"):
            if args.out.lower().endswith(ext):
                args.out = args.out[:-len(ext)]
                break

    coverage = None
    if args.coverage_json and os.path.exists(args.coverage_json):
        try:
            with open(args.coverage_json, "r", encoding="utf-8") as cf:
                coverage = json.load(cf)
        except Exception:
            pass

    findings, opportunities, emp_worker = load_worker_outputs(args.inputs)
    emp_data = emp_worker
    if args.empirical_json and os.path.exists(args.empirical_json):
        try:
            with open(args.empirical_json, "r", encoding="utf-8") as ef:
                ef_json = json.load(ef)
                emp_data = ef_json.get("empirical_corroboration", ef_json)
        except Exception:
            pass

    findings = dedupe(findings)
    report = build_report(
        args.site,
        findings,
        opportunities,
        crawled_pages_count=args.pages_count,
        coverage=coverage,
        empirical_corroboration=emp_data
    )

    out_dir = os.path.dirname(os.path.abspath(f"{args.out}.json"))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    with open(f"{args.out}.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    with open(f"{args.out}.md", "w", encoding="utf-8") as f:
        f.write(render_markdown(report))
    with open(f"{args.out}.html", "w", encoding="utf-8") as f:
        f.write(render_html(report))

    print(f"Wrote {args.out}.json, {args.out}.md, and {args.out}.html ({report['summary']['total_findings']} findings)", file=sys.stderr)


if __name__ == "__main__":
    main()
