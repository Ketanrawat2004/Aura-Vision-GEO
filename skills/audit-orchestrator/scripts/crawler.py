#!/usr/bin/env python3
"""
Lightweight, deterministic internal crawler for the Aura-Vision-GEO audit orchestrator.
Standard library only (urllib, html.parser) with optional Playwright render capture.

Features:
- Sole owner of all target-page fetching (zero redundant worker fetching)
- Respects robots.txt before crawling internal links
- Same-origin only (scheme + hostname matching)
- Avoids duplicate URLs via normalization
- Skips media, binary assets, and downloads
- Extracts PDF link metadata without downloading heavy binaries
- Optional headless render capture at crawl time (if Playwright is present in environment)
- Priority queue prioritizing key paths (/about, /products, /services, /pricing, /contact, /docs, etc.)
- Configurable maximum pages (default: 12)
- Strict timeouts, redirect handling, and safe error recovery
- Emits structured shared page collection:
  [
    {
      "url": "...",
      "status": 200,
      "content_type": "text/html",
      "headers": {...},
      "html": "...",
      "text": "...",
      "title": "...",
      "links": [...],
      "pdf_links": [...],
      "rendered_text": null
    }
  ]
"""
import collections
import gzip
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from html.parser import HTMLParser

USER_AGENT = "Aura-Vision-GEO/2.0 (+read-only site audit; respects robots.txt)"
DEFAULT_TIMEOUT = 5
DEFAULT_MAX_PAGES = 12

IGNORED_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico", ".bmp", ".tiff",
    ".mp4", ".webm", ".avi", ".mov", ".mkv", ".mp3", ".wav", ".ogg",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    ".zip", ".tar", ".gz", ".7z", ".rar", ".exe", ".dmg", ".pkg", ".apk",
    ".css", ".js", ".mjs", ".map", ".json", ".xml", ".csv"
}

PRIORITY_KEYWORDS = [
    "pricing", "price", "plan", "product", "service", "about", "contact",
    "feature", "solution", "company", "docs", "documentation", "faq", "blog", "team"
]


class PageParser(HTMLParser):
    """HTML parser to extract title, visible text, internal links, and PDF links."""

    def __init__(self, base_url: str):
        super().__init__()
        self.base_url = base_url
        self.in_title = False
        self.title = ""
        self._skip_depth = 0
        self.text_chunks = []
        self.links = []
        self.pdf_links = []
        self._current_a_href = None
        self._current_a_text = []

    def _flush_current_a(self):
        if self._current_a_href:
            link_text = " ".join(self._current_a_text).strip()
            resolved = urllib.parse.urljoin(self.base_url, self._current_a_href)
            norm = normalize_url(resolved)
            if resolved.lower().endswith(".pdf") or ".pdf?" in resolved.lower():
                self.pdf_links.append({"url": resolved, "text": link_text})
            elif norm:
                self.links.append({"url": norm, "text": link_text})
            self._current_a_href = None
            self._current_a_text = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == "title":
            self.in_title = True
        elif tag in ("script", "style", "noscript", "svg"):
            self._skip_depth += 1
        elif tag == "a":
            if self._current_a_href:
                self._flush_current_a()
            href = attrs_dict.get("href")
            if href:
                self._current_a_href = href
                self._current_a_text = []

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        elif tag in ("script", "style", "noscript", "svg") and self._skip_depth > 0:
            self._skip_depth -= 1
        elif tag == "a" and self._current_a_href:
            self._flush_current_a()

    def handle_data(self, data):
        if self.in_title:
            self.title += data
        if self._current_a_href is not None:
            self._current_a_text.append(data)
        if self._skip_depth == 0:
            clean = data.strip()
            if clean:
                self.text_chunks.append(clean)


def normalize_url(url: str) -> str:
    """Normalizes URL by stripping fragments and trailing slashes while preserving path."""
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return ""
        clean_path = parsed.path.rstrip("/")
        if not clean_path:
            clean_path = ""
        query = parsed.query
        if query:
            q_pairs = urllib.parse.parse_qsl(query)
            q_filtered = [(k, v) for k, v in q_pairs if not k.lower().startswith(("utm_", "fbclid", "gclid", "session"))]
            query = urllib.parse.urlencode(q_filtered)
        
        normalized = urllib.parse.urlunparse((
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            clean_path if clean_path else "/",
            "",
            query,
            ""
        ))
        return normalized
    except Exception:
        return ""


def is_same_host(host1: str, host2: str) -> bool:
    """Checks whether two hostnames match, treating apex and www subdomains as equivalent."""
    h1 = host1.lower()
    h2 = host2.lower()
    if h1 == h2:
        return True
    if h1.startswith("www.") and h1[4:] == h2:
        return True
    if h2.startswith("www.") and h2[4:] == h1:
        return True
    return False


def is_crawlable_url(url: str, base_netloc: str) -> bool:
    """Determines if the URL belongs to same origin (with www parity) and is an HTML document."""
    try:
        parsed = urllib.parse.urlparse(url)
        if not is_same_host(parsed.netloc, base_netloc):
            return False
        path_lower = parsed.path.lower()
        for ext in IGNORED_EXTENSIONS:
            if path_lower.endswith(ext):
                return False
        return True
    except Exception:
        return False


def score_url_priority(url: str) -> int:
    """Scores a URL for crawling priority. Lower number = higher priority."""
    path = urllib.parse.urlparse(url).path.lower()
    if path in ("", "/"):
        return 0
    for idx, kw in enumerate(PRIORITY_KEYWORDS):
        if kw in path:
            return idx + 1
    return 100


def get_robots_parser(site_url: str, timeout: int = DEFAULT_TIMEOUT):
    """Fetches and parses robots.txt for the given site."""
    robots_url = urllib.parse.urljoin(site_url, "/robots.txt")
    rfp = urllib.robotparser.RobotFileParser()
    rfp.set_url(robots_url)
    try:
        req = urllib.request.Request(robots_url, headers={"User-Agent": USER_AGENT})
        try:
            resp = urllib.request.urlopen(req, timeout=timeout)
        except urllib.error.URLError as e:
            if "CERTIFICATE_VERIFY_FAILED" in str(e):
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                resp = urllib.request.urlopen(req, timeout=timeout, context=ctx)
            else:
                raise
        with resp:
            content = resp.read().decode("utf-8", errors="replace")
            rfp.parse(content.splitlines())
    except urllib.error.HTTPError as e:
        if e.code in (404, 410):
            rfp.allow_all = True
        elif e.code in (401, 403):
            rfp.disallow_all = True
        else:
            rfp.allow_all = True
    except Exception:
        rfp.allow_all = True
    return rfp


def fetch_page(url: str, timeout: int = DEFAULT_TIMEOUT):
    """Fetches a single page and returns status, headers, and decoded HTML."""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
    )
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.URLError as e:
        if "CERTIFICATE_VERIFY_FAILED" in str(e):
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            resp = urllib.request.urlopen(req, timeout=timeout, context=ctx)
        else:
            raise

    with resp:
        status = resp.status
        headers = dict(resp.getheaders())
        raw_bytes = resp.read()
        
        ce = headers.get("content-encoding", "").lower()
        if raw_bytes.startswith(b"\x1f\x8b") or "gzip" in ce:
            try:
                raw_bytes = gzip.decompress(raw_bytes)
            except Exception:
                pass
        elif "deflate" in ce:
            try:
                import zlib
                raw_bytes = zlib.decompress(raw_bytes, -zlib.MAX_WBITS)
            except Exception:
                try:
                    import zlib
                    raw_bytes = zlib.decompress(raw_bytes)
                except Exception:
                    pass
        
        content_type = headers.get("content-type", "text/html")
        charset = "utf-8"
        if "charset=" in content_type.lower():
            try:
                charset = content_type.lower().split("charset=")[-1].split(";")[0].strip().strip('"\'')
            except Exception:
                pass
        
        try:
            html = raw_bytes.decode(charset, errors="replace")
        except (LookupError, Exception):
            html = raw_bytes.decode("utf-8", errors="replace")
        return status, content_type, headers, html


def try_render_page(url: str, timeout: int = DEFAULT_TIMEOUT):
    """
    Optional single-pass headless render using Playwright if installed in the environment.
    Executed strictly during the orchestrator's ingestion phase so worker skills never
    perform redundant fetches.
    """
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except ImportError:
        return None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(user_agent=USER_AGENT)
            page.goto(url, timeout=timeout * 1000, wait_until="networkidle")
            content = page.inner_text("body")
            browser.close()
            return content
    except Exception:
        return None


def crawl_website(start_url: str, max_pages: int = DEFAULT_MAX_PAGES, timeout: int = DEFAULT_TIMEOUT, respect_robots: bool = True):
    """
    Crawls website starting from start_url up to max_pages.
    Returns list of page dictionaries.
    """
    start_time = time.time()
    if not start_url.startswith("http://") and not start_url.startswith("https://"):
        start_url = "https://" + start_url

    norm_start = normalize_url(start_url)
    if not norm_start:
        norm_start = start_url

    parsed_start = urllib.parse.urlparse(norm_start)
    base_netloc = parsed_start.netloc.lower()

    rfp = get_robots_parser(norm_start, timeout=timeout) if respect_robots else None

    visited = set()
    queue = []
    pages = []

    queue.append((0, norm_start))
    visited.add(norm_start)

    while queue and len(pages) < max_pages:
        if time.time() - start_time > 180:
            print(f"Crawler reached runtime safety limit (180s). Concluding crawl with {len(pages)} pages.", file=sys.stderr)
            break

        queue.sort(key=lambda x: x[0])
        _, current_url = queue.pop(0)

        if rfp and not rfp.can_fetch(USER_AGENT, current_url):
            pages.append({
                "url": current_url,
                "status": 403,
                "content_type": "text/html",
                "headers": {},
                "html": "",
                "text": "",
                "title": "Disallowed by robots.txt",
                "links": [],
                "pdf_links": [],
                "rendered_text": None,
                "error": "Disallowed by robots.txt"
            })
            continue

        try:
            status, content_type, headers, html = fetch_page(current_url, timeout=timeout)
        except urllib.error.HTTPError as e:
            pages.append({
                "url": current_url,
                "status": e.code,
                "content_type": "text/html",
                "headers": dict(e.headers) if hasattr(e, "headers") else {},
                "html": "",
                "text": "",
                "title": f"HTTP {e.code} Error",
                "links": [],
                "pdf_links": [],
                "rendered_text": None,
                "error": str(e)
            })
            continue
        except Exception as e:
            pages.append({
                "url": current_url,
                "status": 0,
                "content_type": "",
                "headers": {},
                "html": "",
                "text": "",
                "title": "Fetch Error",
                "links": [],
                "pdf_links": [],
                "rendered_text": None,
                "error": str(e)
            })
            continue

        if "text/html" not in content_type.lower() and "application/xhtml" not in content_type.lower():
            pages.append({
                "url": current_url,
                "status": status,
                "content_type": content_type,
                "headers": headers,
                "html": "",
                "text": "",
                "title": "Non-HTML Content",
                "links": [],
                "pdf_links": [],
                "rendered_text": None,
                "error": f"Content-Type is {content_type} (expected text/html)"
            })
            continue

        parser = PageParser(current_url)
        try:
            parser.feed(html)
        except Exception:
            pass

        title = parser.title.strip()
        text = " ".join(parser.text_chunks)

        # Optional single-pass headless render capture if an SPA container is present
        rendered_text = None
        if re.search(r'id=["\'](?:root|app)["\']|<app-root\b', html, re.IGNORECASE):
            rendered_text = try_render_page(current_url, timeout=timeout)

        page_record = {
            "url": current_url,
            "status": status,
            "content_type": content_type,
            "headers": headers,
            "html": html,
            "text": text,
            "title": title,
            "links": [link["url"] for link in parser.links],
            "pdf_links": parser.pdf_links,
            "rendered_text": rendered_text
        }
        if not html.strip():
            page_record["error"] = "Empty or blank HTML payload received (0 bytes content)"
        pages.append(page_record)

        for link_obj in parser.links:
            target_url = link_obj["url"]
            if target_url not in visited and is_crawlable_url(target_url, base_netloc):
                visited.add(target_url)
                prio = score_url_priority(target_url)
                queue.append((prio, target_url))

    if not pages:
        pages.append({
            "url": norm_start,
            "status": 0,
            "content_type": "",
            "headers": {},
            "html": "",
            "text": "",
            "title": "Fetch Error",
            "links": [],
            "pdf_links": [],
            "rendered_text": None,
            "error": "Zero pages retrieved from host"
        })

    return pages


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Lightweight internal crawler for Aura-Vision-GEO")
    parser.add_argument("url", help="Root website URL to crawl")
    parser.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES, help="Max pages to crawl")
    parser.add_argument("--out", help="Path to write pages JSON")
    args = parser.parse_args()

    results = crawl_website(args.url, max_pages=args.max_pages)
    print(f"Crawled {len(results)} pages from {args.url}", file=sys.stderr)
    for p in results:
        print(f" - [{p['status']}] {p['url']} ({len(p.get('text', '').split())} words, {len(p.get('pdf_links', []))} PDFs)", file=sys.stderr)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"Saved to {args.out}", file=sys.stderr)
