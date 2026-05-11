"""Fetch BuiltIn (builtin.com) job postings via HTTP + BeautifulSoup.

BuiltIn provides:
- Category pages: /jobs/dev-engineering/data-engineering
- A `?search=<query>` parameter for text search
- A `?company-size=50,251` URL filter (lower,upper bounds; BuiltIn uses 251 as
  the 250-employee bucket upper edge, hence the value)
- Paginated results at ?page=N
- Each search/category page exposes JSON-LD ItemList (first 25 results) with
  `name`, `url`, `description`
- Each detail page exposes JSON-LD JobPosting schema with title, full HTML
  description, jobLocation.address, validThrough, employmentType, datePosted

This fetcher iterates a small set of (category + search-term) tuples covering
the role titles methodology.md includes (Data Engineer, Analytics Engineer,
Data Platform Engineer), with company-size pre-filter, and writes one record
per detail page into raw JSONL.

Usage:
    python fetch_builtin.py                              # default: 5 pages per role
    python fetch_builtin.py --max-pages 3
    python fetch_builtin.py --roles data_engineer
    python fetch_builtin.py --dry-run                    # list URLs, don't fetch detail

Output:
    $CAPTURE_DIR/raw/builtin-<role>-<page>.jsonl   one record per posting

Record shape (same family as fetch_hn.py output):
    {
      "posting_id": "<sha1 of source_url + posting_date>",
      "source": "builtin",
      "source_url": "https://builtin.com/job/...",
      "captured_date": "YYYY-MM-DD",
      "posting_date": "YYYY-MM-DD",        # from datePosted in JD JSON-LD
      "raw_text": "<plaintext JD body>",
      "raw_html": "<HTML JD body verbatim>",
      "title": "Data Engineer",
      "company_alias": "ibotta",            # parsed from /company/<alias>
      "location_text": "Denver, Colorado, USA",
      "search_role": "data_engineer",       # which role-search produced this row
    }

Notes:
- BuiltIn employs Cloudflare; bursts of 50+ rapid requests trigger 429s.
  Default per-request delay: 0.3s. Override via --sleep.
- The schema.org JobPosting block is keyed off the `JobPosting` string anywhere
  in any <script>; we don't rely on the standard `<script type="application/ld+json">`
  tag because BuiltIn embeds it raw.
"""
from __future__ import annotations

import argparse
import html as html_lib
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Iterator

import requests
from bs4 import BeautifulSoup

from common import (
    posting_id,
    raw_dir,
    today_iso,
    write_jsonl,
)


BASE = "https://builtin.com"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
DEFAULT_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


# ---- Search profiles ----

# (search_role, category_path, search_query). category_path may be empty to use
# /jobs/ root. search_query supplements the category narrowing.
SEARCH_PROFILES: dict[str, tuple[str, str]] = {
    # The dev-engineering/data-engineering category already covers DE-flavored
    # roles broadly. We add a search term to bias toward titles the methodology
    # treats as in-scope.
    "data_engineer": ("/jobs/dev-engineering/data-engineering", "data engineer"),
    "analytics_engineer": ("/jobs/dev-engineering/data-engineering", "analytics engineer"),
    "data_platform_engineer": ("/jobs/dev-engineering/data-engineering", "data platform engineer"),
}


# ---- HTTP helpers ----

def _get(url: str, *, session: requests.Session, sleep_s: float) -> str:
    if sleep_s > 0:
        time.sleep(sleep_s)
    r = session.get(url, headers=DEFAULT_HEADERS, timeout=30)
    r.raise_for_status()
    return r.text


# ---- Search page parsing ----

_JSONLD_BLOCK_RE = re.compile(r'<script[^>]*>(\s*\{[^<]*?"@context"[^<]*?\})\s*</script>', re.S)


def _extract_jsonld_blocks(html: str) -> list[dict]:
    out: list[dict] = []
    # Match either standard ld+json scripts or unmarked schema scripts.
    for m in re.finditer(r'<script[^>]*>(\s*\{[\s\S]*?\})\s*</script>', html):
        raw = m.group(1).strip()
        if '"@context"' not in raw or "schema.org" not in raw:
            continue
        # Unescape HTML entities that sometimes appear in href tracking links.
        raw = raw.replace("&#x2B;", "+").replace("&amp;", "&")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        out.append(data)
    return out


def _search_page_url(category_path: str, search: str, page: int,
                     company_size: str = "50,251") -> str:
    from urllib.parse import urlencode
    params = {"company-size": company_size}
    if search:
        params["search"] = search
    if page > 1:
        params["page"] = str(page)
    qs = urlencode(params)
    return f"{BASE}{category_path}?{qs}"


def _list_candidates_from_search_page(html: str) -> list[dict]:
    """Pull title + URL + description from the JSON-LD ItemList block(s)."""
    out: list[dict] = []
    for blob in _extract_jsonld_blocks(html):
        graph = blob.get("@graph") or [blob]
        for item in graph:
            if item.get("@type") == "ItemList":
                for el in item.get("itemListElement", []):
                    name = el.get("name") or ""
                    url = el.get("url") or ""
                    desc = el.get("description") or ""
                    if url:
                        out.append({"title": name, "url": url, "description": desc})
    return out


# ---- Detail page parsing ----

def _extract_jobposting(html: str) -> dict | None:
    """Pull the JobPosting node from any JSON-LD block on the detail page."""
    for blob in _extract_jsonld_blocks(html):
        graph = blob.get("@graph") or [blob]
        for item in graph:
            if item.get("@type") == "JobPosting":
                return item
    return None


def _strip_html(html: str) -> str:
    """Convert JD HTML to plaintext using BS4. Preserve paragraph breaks.

    BuiltIn JDs are HTML-heavy: <b>About Company</b><p>...</p><p>...</p><ul><li>...
    Naive get_text() jams the <b> header straight into the next <p>. We:
      1. Replace <br> with newline.
      2. Insert a newline before each block-level element so siblings don't fuse.
      3. Call get_text with newline separator.
      4. Collapse runs of 3+ newlines.
    """
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all("br"):
        tag.replace_with("\n")
    for tag in soup.find_all(["p", "li", "h1", "h2", "h3", "h4", "h5", "h6",
                              "div", "section", "ul", "ol"]):
        tag.insert_before("\n")
        tag.insert_after("\n")
    text = soup.get_text(separator=" ")
    text = html_lib.unescape(text)
    # Tighten whitespace inside lines but keep line breaks.
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def _company_alias_from_html(html: str) -> str:
    m = re.search(r'href="/company/([a-zA-Z0-9._\-]+)"', html)
    return m.group(1) if m else ""


def _location_from_jobposting(jp: dict) -> str:
    loc = jp.get("jobLocation") or {}
    if isinstance(loc, list):
        loc = loc[0] if loc else {}
    addr = loc.get("address") or {}
    parts = [
        addr.get("addressLocality") or "",
        addr.get("addressRegion") or "",
        addr.get("addressCountry") or "",
    ]
    return ", ".join(p for p in parts if p)


def _date_posted(jp: dict) -> str:
    raw = jp.get("datePosted") or ""
    if not raw:
        return ""
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")) \
            .astimezone(timezone.utc).date().isoformat()
    except ValueError:
        return raw[:10]


# ---- Top-level iteration ----

@dataclass(frozen=True)
class Candidate:
    role: str
    title: str
    url: str
    description: str  # short blurb from the search-results JSON-LD


def iter_search_candidates(
    role: str, category_path: str, search: str, *,
    max_pages: int, session: requests.Session, sleep_s: float,
) -> Iterator[Candidate]:
    seen: set[str] = set()
    for page in range(1, max_pages + 1):
        url = _search_page_url(category_path, search, page)
        try:
            html = _get(url, session=session, sleep_s=sleep_s)
        except requests.HTTPError as e:
            print(f"  [{role}] page {page} failed: {e}", file=sys.stderr)
            return
        items = _list_candidates_from_search_page(html)
        if not items:
            return
        new_on_page = 0
        for it in items:
            u = it["url"]
            if u in seen:
                continue
            seen.add(u)
            new_on_page += 1
            yield Candidate(role=role, title=it["title"], url=u, description=it["description"])
        if new_on_page == 0:
            return  # nothing new on this page; remaining pages will be the same


def fetch_detail(url: str, *, session: requests.Session, sleep_s: float) -> dict | None:
    """Fetch one detail page and return the raw posting dict, or None on failure."""
    try:
        html = _get(url, session=session, sleep_s=sleep_s)
    except requests.HTTPError as e:
        print(f"  detail fetch failed for {url}: {e}", file=sys.stderr)
        return None
    jp = _extract_jobposting(html)
    if not jp:
        return None
    desc_html = jp.get("description") or ""
    raw_text = _strip_html(desc_html)
    # The plaintext doesn't include the title or location — prepend them in a
    # consistent first-line format so downstream filter/extract sees the same
    # shape as HN postings: "Company | Role | Location".
    company_alias = _company_alias_from_html(html)
    location = _location_from_jobposting(jp)
    title = jp.get("title") or ""
    composed_first_line = " | ".join(p for p in [company_alias or "company", title, location] if p)
    body = composed_first_line + "\n\n" + raw_text

    posting_date = _date_posted(jp)
    return {
        "source": "builtin",
        "source_url": url,
        "captured_date": today_iso(),
        "posting_date": posting_date,
        "raw_text": body,
        "raw_html": desc_html,
        "title": title,
        "company_alias": company_alias,
        "location_text": location,
        "posting_id": posting_id(url, posting_date or None),
    }


# ---- CLI ----

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Fetch BuiltIn job postings via HTTP + BS4.")
    p.add_argument("--roles", nargs="*", default=None,
                   help=f"Roles to fetch (default: all). Choices: {list(SEARCH_PROFILES)}")
    p.add_argument("--max-pages", type=int, default=5,
                   help="Max search-result pages per role. Default 5 (~125 candidates per role).")
    p.add_argument("--sleep", type=float, default=0.3,
                   help="Seconds between HTTP requests in a single worker. Default 0.3.")
    p.add_argument("--concurrency", type=int, default=1,
                   help="Concurrent detail-page fetches. Each worker owns its own "
                        "requests.Session. Default 1 (sequential).")
    p.add_argument("--dry-run", action="store_true",
                   help="List candidate URLs without fetching detail pages.")
    args = p.parse_args(argv)

    roles = args.roles or list(SEARCH_PROFILES.keys())
    invalid = [r for r in roles if r not in SEARCH_PROFILES]
    if invalid:
        print(f"Unknown roles: {invalid}", file=sys.stderr)
        return 2

    out_dir = raw_dir()
    sess = requests.Session()
    total_records = 0

    for role in roles:
        category_path, search_query = SEARCH_PROFILES[role]
        candidates = list(iter_search_candidates(
            role, category_path, search_query,
            max_pages=args.max_pages, session=sess, sleep_s=args.sleep,
        ))
        print(f"[{role}] discovered {len(candidates)} candidate URLs across "
              f"<= {args.max_pages} pages")
        if args.dry_run:
            for c in candidates[:10]:
                print(f"  - {c.title[:60]:60}  {c.url}")
            if len(candidates) > 10:
                print(f"  ... and {len(candidates) - 10} more")
            continue
        records: list[dict] = []
        if args.concurrency <= 1:
            for c in candidates:
                rec = fetch_detail(c.url, session=sess, sleep_s=args.sleep)
                if rec is None:
                    continue
                rec["search_role"] = role
                records.append(rec)
        else:
            # Concurrent detail fetches. Each worker uses its own Session because
            # requests.Session isn't thread-safe under heavy concurrent use.
            def _one(url: str) -> dict | None:
                local = requests.Session()
                # Stagger the launch window so we don't 25-burst a single edge.
                return fetch_detail(url, session=local, sleep_s=args.sleep)
            with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
                futures = {pool.submit(_one, c.url): c for c in candidates}
                for fut in as_completed(futures):
                    c = futures[fut]
                    rec = fut.result()
                    if rec is None:
                        continue
                    rec["search_role"] = role
                    records.append(rec)
        out_path = out_dir / f"builtin-{role}.jsonl"
        n = write_jsonl(out_path, records)
        total_records += n
        print(f"  -> {out_path.name}  ({n} postings)")

    if not args.dry_run:
        print(f"\nWrote {total_records} BuiltIn postings to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
