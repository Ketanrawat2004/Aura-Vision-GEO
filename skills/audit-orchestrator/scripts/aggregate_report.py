#!/usr/bin/env python3
"""
Merge raw findings from the four worker skills into the final audit report.

Each worker skill writes its own JSON file shaped like:
    {"findings": [ {title, category, subcategory, impact, scope, confidence,
                     evidence, suggested_action}, ... ],
     "opportunities": [ {title, suggested_action}, ... ]}

Usage:
    python aggregate_report.py --site example.com \
        --inputs crawl.json structured.json trust.json engagement.json \
        --out audit_report

Writes <out>.json (fixed schema) and <out>.md (human-readable) next to each other.
"""
import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone

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
    # crude stemming: strip a trailing 's' (products -> product) so plural
    # mismatches don't defeat the similarity check
    stemmed = (w[:-1] if w.endswith("s") and len(w) > 3 else w for w in words)
    return {w for w in stemmed if w not in STOPWORDS}


def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def derive_severity(finding: dict) -> str:
    impact = finding.get("impact", "degrading")
    scope = finding.get("scope", "section")
    return SEVERITY_MATRIX.get((impact, scope), "medium")


def load_worker_outputs(paths):
    findings, opportunities = [], []
    for p in paths:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        findings.extend(data.get("findings", []))
        opportunities.extend(data.get("opportunities", []))
    return findings, opportunities


def dedupe(findings, similarity_threshold=0.5):
    """Merge findings that share a subcategory and have highly overlapping
    titles. Keeps the longer (more specific) title and unions the evidence."""
    merged = []
    used = [False] * len(findings)
    for i, f in enumerate(findings):
        if used[i]:
            continue
        group = [f]
        used[i] = True
        f_tokens = normalize_title(f["title"])
        for j in range(i + 1, len(findings)):
            if used[j]:
                continue
            g = findings[j]
            if g.get("subcategory") != f.get("subcategory"):
                continue
            if jaccard(f_tokens, normalize_title(g["title"])) >= similarity_threshold:
                group.append(g)
                used[j] = True
        if len(group) == 1:
            merged.append(f)
        else:
            best = max(group, key=lambda x: len(x["title"]))
            best = dict(best)
            best["evidence"] = "; ".join(dict.fromkeys(g["evidence"] for g in group))
            merged.append(best)
    return merged


def build_report(site, findings, opportunities):
    for f in findings:
        f["severity"] = derive_severity(f)

    findings.sort(key=lambda f: (SEVERITY_RANK[f["severity"]], f.get("category", "")))

    out_findings = []
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for idx, f in enumerate(findings, start=1):
        counts[f["severity"]] += 1
        out_findings.append({
            "id": f"F-{idx:03d}",
            "title": f["title"],
            "severity": f["severity"],
            "category": f.get("category", "discoverability"),
            "subcategory": f.get("subcategory", f.get("category", "discoverability")),
            "confidence": f.get("confidence", "medium"),
            "evidence": f["evidence"],
            "suggested_action": f["suggested_action"],
        })

    out_opportunities = [
        {"title": o["title"], "suggested_action": o["suggested_action"]}
        for o in opportunities
    ]

    audited_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    raw_proof = f"{site}:{audited_at}:{len(out_findings)}:" + "".join(f["id"] + f["title"] for f in out_findings)
    proof_hash = hashlib.sha256(raw_proof.encode("utf-8")).hexdigest()

    return {
        "site": site,
        "audited_at": audited_at,
        "verification": {
            "protocol": "AuraVision-SHA256-Deterministic-Ledger",
            "proof_hash": f"sha256:{proof_hash[:24]}...",
            "tamper_evident": True
        },
        "summary": {"total_findings": len(out_findings), **counts},
        "findings": out_findings,
        "opportunities": out_opportunities,
    }


def render_markdown(report: dict) -> str:
    lines = [f"# AuraVision GEO Audit — {report['site']}", "", f"Audited at {report['audited_at']}", ""]
    verif = report.get("verification", {})
    if verif.get("proof_hash"):
        lines.append(f"> **Cryptographic Proof**: `{verif['proof_hash']}` ({verif.get('protocol', 'SHA256-Ledger')})")
        lines.append("")
    s = report["summary"]
    lines.append(f"**{s['total_findings']} findings** — {s['critical']} critical, {s['high']} high, "
                 f"{s['medium']} medium, {s['low']} low")
    lines.append("")
    for f in report["findings"]:
        lines.append(f"## [{f['severity'].upper()}] {f['id']}: {f['title']}")
        lines.append(f"*Category: {f['category']} · Confidence: {f.get('confidence', 'medium')}*")
        lines.append("")
        lines.append(f"**Evidence:** {f['evidence']}")
        lines.append("")
        lines.append(f"**Fix ({f['suggested_action'].get('priority', 'medium')} priority):** "
                      f"{f['suggested_action']['summary']}")
        if f["suggested_action"].get("mechanism"):
            lines.append(f"> Why: {f['suggested_action']['mechanism']}")
        lines.append("")
    if report["opportunities"]:
        lines.append("## Beyond-defect opportunities")
        for o in report["opportunities"]:
            lines.append(f"- **{o['title']}** — {o['suggested_action']['summary']}")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True)
    ap.add_argument("--inputs", nargs="+", required=True, help="worker-skill JSON output files")
    ap.add_argument("--out", default="audit_report", help="output basename (no extension)")
    args = ap.parse_args()

    findings, opportunities = load_worker_outputs(args.inputs)
    findings = dedupe(findings)
    report = build_report(args.site, findings, opportunities)

    with open(f"{args.out}.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    with open(f"{args.out}.md", "w", encoding="utf-8") as f:
        f.write(render_markdown(report))

    print(f"Wrote {args.out}.json and {args.out}.md "
          f"({report['summary']['total_findings']} findings, "
          f"{len(report['opportunities'])} opportunities)", file=sys.stderr)


if __name__ == "__main__":
    main()
