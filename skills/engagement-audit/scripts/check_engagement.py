#!/usr/bin/env python3
"""
On-site engagement checks. Stdlib-only.

Usage:
    python check_engagement.py --pages https://example.com https://example.com/pricing \
        --out engagement_findings.json
"""
import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from urllib.parse import urljoin, urlparse

USER_AGENT = "Aura-Vision-GEO/1.0 (+read-only site audit)"
TIMEOUT = 10
MAX_LINKS_TO_CHECK = 8

NAV_RE = re.compile(r'<nav\b', re.IGNORECASE)
VIEWPORT_RE = re.compile(r'<meta[^>]+name=["\']viewport["\']', re.IGNORECASE)
LINK_RE = re.compile(r'<a\b[^>]*href=["\']([^"\'#][^"\']*)["\'][^>]*>(.*?)</a>',
                      re.IGNORECASE | re.DOTALL)
BTN_RE = re.compile(r'<(button|a)\b[^>]*class=["\'][^"\']*\bbtn[^"\']*["\'][^>]*>(.*?)</\1>',
                     re.IGNORECASE | re.DOTALL)
GENERIC_CTA_TEXT = {"click here", "here", "this", "submit", "go", "more", "learn more"}
PARA_RE = re.compile(r'<p\b[^>]*>(.*?)</p>', re.IGNORECASE | re.DOTALL)
CONTACT_LINK_RE = re.compile(r'href=["\'][^"\']*(contact|about)[^"\']*["\']', re.IGNORECASE)


def strip_tags(html):
    # Remove cookie / consent banners before evaluating prose text
    cleaned = re.sub(r'<div[^>]*(?:cookie|consent|banner|modal)[^>]*>.*?</div>', ' ', html, flags=re.IGNORECASE | re.DOTALL)
    return re.sub(r"<[^>]+>", " ", cleaned).strip()


def fetch(url, method="GET"):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT}, method=method)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.status, resp.read().decode("utf-8", errors="replace") if method == "GET" else ""


def check_page(url, html):
    findings = []
    parsed_base = urlparse(url)

    if not NAV_RE.search(html):
        findings.append(_finding(
            "No <nav> element found", "navigation", "degrading", "sitewide", "medium",
            f"No <nav> tag in {url}.",
            "Wrap primary navigation in a <nav> element with descriptive link text.", "medium"))

    if not VIEWPORT_RE.search(html):
        findings.append(_finding(
            "No mobile viewport meta tag", "navigation", "degrading", "sitewide", "high",
            f"No <meta name=\"viewport\"> found on {url}.",
            "Add <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">.",
            "medium"))

    # CTA clarity
    generic_ctas = []
    for _tag, inner in BTN_RE.findall(html):
        text = strip_tags(inner).strip().lower()
        if text in GENERIC_CTA_TEXT:
            generic_ctas.append(text)
    if generic_ctas:
        findings.append(_finding(
            f"{len(generic_ctas)} generic call-to-action label(s)", "orientation",
            "cosmetic", "section", "medium",
            f"CTA text with no surrounding context: {generic_ctas[:5]}",
            "Use specific CTA text (\"Start free trial\" not \"Click here\").", "low"))

    # Scannability
    paras = [strip_tags(p) for p in PARA_RE.findall(html)]
    word_counts = [len(p.split()) for p in paras if p]
    if word_counts:
        avg_words = sum(word_counts) / len(word_counts)
        if avg_words > 120 and max(word_counts) > 150:
            findings.append(_finding(
                "Long, unbroken paragraphs", "orientation", "cosmetic", "section", "low",
                f"{url}: average {avg_words:.0f} words/paragraph across {len(word_counts)} "
                f"paragraphs; longest is {max(word_counts)} words.",
                "Break long paragraphs up with subheadings, bullets, or shorter grafs.", "low"))

    # Trust signals
    if not CONTACT_LINK_RE.search(html):
        findings.append(_finding(
            "No contact/about link found", "trust-signals", "degrading", "sitewide", "medium",
            f"No link containing 'contact' or 'about' found on {url}.",
            "Add a visible link to a contact or about page from primary navigation.", "medium"))

    return findings, extract_internal_links(url, html)


def extract_internal_links(base_url, html):
    base = urlparse(base_url)
    links = []
    for href, _text in LINK_RE.findall(html):
        abs_url = urljoin(base_url, href)
        p = urlparse(abs_url)
        if p.netloc == base.netloc and p.scheme in ("http", "https"):
            links.append(abs_url)
    # de-dupe, cap
    seen = []
    for l in links:
        if l not in seen:
            seen.append(l)
    return seen[:MAX_LINKS_TO_CHECK]


def check_dead_links(links):
    findings = []
    dead = []
    for url in links:
        try:
            status, _ = fetch(url, method="GET")
            if status >= 400:
                dead.append((url, status))
        except urllib.error.HTTPError as e:
            dead.append((url, e.code))
        except Exception:
            dead.append((url, "unreachable"))
    if dead:
        scope = "sitewide" if len(dead) >= max(3, len(links) // 2) else "section"
        findings.append(_finding(
            f"{len(dead)} internal link(s) lead to dead ends", "navigation",
            "degrading", scope, "high",
            f"Broken internal links: {dead[:8]}",
            "Fix or remove these internal links.", "medium"))
    return findings


def _finding(title, subcategory, impact, scope, confidence, evidence, action_summary, priority):
    return {
        "title": title,
        "category": "engagement",
        "subcategory": subcategory,
        "impact": impact,
        "scope": scope,
        "confidence": confidence,
        "evidence": evidence,
        "suggested_action": {"summary": action_summary, "priority": priority},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", nargs="+", required=True)
    ap.add_argument("--out", default="engagement_findings.json")
    args = ap.parse_args()

    all_findings = []
    all_internal_links = []
    for url in args.pages:
        try:
            _status, html = fetch(url)
        except Exception as e:
            print(f"warning: could not fetch {url}: {e}", file=sys.stderr)
            continue
        findings, links = check_page(url, html)
        all_findings.extend(findings)
        all_internal_links.extend(links)

    # cap total dead-link checks across the whole run to respect the time budget
    sample = all_internal_links[:MAX_LINKS_TO_CHECK]
    all_findings.extend(check_dead_links(sample))

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"findings": all_findings, "opportunities": []}, f, indent=2, ensure_ascii=False)
    print(f"Wrote {args.out}: {len(all_findings)} findings", file=sys.stderr)


if __name__ == "__main__":
    main()
