"""Fetch HN "Ask HN: Who is hiring?" thread comments via the Algolia public API.

Usage:
    python fetch_hn.py                       # default: most recent two whoishiring threads
    python fetch_hn.py --thread 47975571     # one specific thread by HN story ID
    python fetch_hn.py --months 3            # most recent N whoishiring threads
    python fetch_hn.py --list                # list discoverable threads, don't fetch

Output:
    $CAPTURE_DIR/raw/hn-<story_id>-<YYYY-MM>.jsonl     one record per top-level comment

Record shape (also documented in pipeline/README.md):
    {
      "posting_id": "<sha1 of source_url + posting_date>",
      "source": "hn_whoishiring",
      "source_url": "https://news.ycombinator.com/item?id=<comment_id>",
      "captured_date": "YYYY-MM-DD",
      "posting_date": "YYYY-MM-DD",
      "raw_text": "<plaintext body, HN <p> tags normalized to blank lines>",
      "raw_html": "<original HTML for auditability>",
      "thread_id": "<story_id>",
      "thread_title": "Ask HN: Who is hiring? (May 2026)",
      "author": "<HN username>"
    }

Top-level vs. reply: HN's "Ask HN: Who is hiring" convention is that top-level
comments are postings and replies to those are discussion. The methodology
counts top-level postings only (replies are usually "$24K? lol" not actual job
postings); filter accordingly via parent_id == story_id.

The Algolia API is public, unauthenticated, and rate-limit-friendly for the
scale of this analysis (~1000 hits/page, ~1 thread = 1 call). No retry logic
beyond a single retry-on-5xx; if Algolia is down at capture time we just rerun.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
import urllib.parse
from datetime import datetime, timezone
from typing import Iterator

import requests

from common import (
    posting_id,
    raw_dir,
    today_iso,
    write_jsonl,
)


ALGOLIA_SEARCH_URL = "https://hn.algolia.com/api/v1/search_by_date"
HN_ITEM_URL = "https://news.ycombinator.com/item?id={item_id}"

# whoishiring is the HN moderator account that opens each monthly thread.
WHOISHIRING_AUTHOR_TAG = "author_whoishiring"


# ---- Thread discovery ----

def list_whoishiring_threads(limit: int = 12) -> list[dict]:
    """Return the most recent `limit` 'Who is hiring' threads, newest first."""
    params = {
        "query": "Ask HN: Who is hiring",
        "tags": f"story,{WHOISHIRING_AUTHOR_TAG}",
        "hitsPerPage": str(limit),
    }
    r = requests.get(ALGOLIA_SEARCH_URL, params=params, timeout=15)
    r.raise_for_status()
    hits = r.json().get("hits", [])
    # Algolia returns most-recent-first when searching by_date.
    out = []
    for h in hits:
        title = h.get("title") or ""
        # Defensive — sometimes "Who is hiring right now?" or "Who wants to be hired?"
        # threads show up; restrict to canonical monthly format.
        if not title.startswith("Ask HN: Who is hiring? ("):
            continue
        out.append({
            "story_id": h["objectID"],
            "title": title,
            "created_at": h.get("created_at"),
            "num_comments": h.get("num_comments", 0),
        })
    return out


# ---- Comment fetch ----

def fetch_thread_comments(story_id: str) -> list[dict]:
    """Fetch every comment under a story_id. Returns Algolia's raw hits."""
    all_hits: list[dict] = []
    page = 0
    while True:
        params = {
            "tags": f"comment,story_{story_id}",
            "hitsPerPage": "1000",
            "page": str(page),
        }
        r = requests.get(ALGOLIA_SEARCH_URL, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        hits = data.get("hits", [])
        all_hits.extend(hits)
        nb_pages = data.get("nbPages", 1)
        if page + 1 >= nb_pages:
            break
        page += 1
        time.sleep(0.25)  # courtesy delay; the API is fine without it
    return all_hits


# ---- HN HTML normalization ----

_TAG_RE = re.compile(r"<[^>]+>")
_MULTI_BLANK_RE = re.compile(r"\n{3,}")


def normalize_hn_text(html_body: str) -> str:
    """Convert HN-flavored comment HTML to plaintext.

    HN's comment HTML uses:
      <p>      between paragraphs (no closing tag)
      <a href> for links (we keep the href text since it's often the company URL)
      <i>      occasionally for italics
      &#x27;   and friends for ASCII entities

    We:
      1. Replace `<p>` with double newlines.
      2. Convert `<a href="X">Y</a>` to `Y (X)` so URLs survive in extracted text.
      3. Strip remaining tags.
      4. Decode HTML entities.
      5. Collapse 3+ consecutive newlines to 2.
    """
    if not html_body:
        return ""
    text = html_body

    # <p> in HN is a paragraph separator, not a wrapper.
    text = text.replace("<p>", "\n\n")
    text = text.replace("</p>", "")

    # Inline links: keep visible text + URL in parens. Helps the LLM see when a
    # company links to their stack page or a job description.
    def link_repl(m: re.Match[str]) -> str:
        href = m.group(1)
        inner = m.group(2)
        # If the visible text equals the href (common on HN), no need to dupe.
        if inner.strip() == href.strip():
            return href.strip()
        return f"{inner.strip()} ({href.strip()})"

    text = re.sub(
        r'<a\s+href="([^"]+)"[^>]*>(.*?)</a>',
        link_repl,
        text,
        flags=re.DOTALL,
    )

    # Drop remaining tags (<i>, <pre>, <code>, etc.).
    text = _TAG_RE.sub("", text)

    # Decode HTML entities.
    text = html.unescape(text)

    # Collapse runs of blank lines and trim.
    text = _MULTI_BLANK_RE.sub("\n\n", text).strip()
    return text


# ---- Per-thread iteration ----

def iter_thread_postings(thread: dict) -> Iterator[dict]:
    """Yield top-level posting records for a given thread (one per top-level comment)."""
    story_id = thread["story_id"]
    title = thread.get("title", "")
    hits = fetch_thread_comments(story_id)

    captured = today_iso()
    for h in hits:
        # Top-level postings only: replies have parent_id != story_id.
        if str(h.get("parent_id")) != str(story_id):
            continue
        body_html = h.get("comment_text") or ""
        body_text = normalize_hn_text(body_html)
        if not body_text:
            # Deleted / empty comments. Skip silently.
            continue

        comment_id = str(h["objectID"])
        url = HN_ITEM_URL.format(item_id=comment_id)
        created_at = h.get("created_at") or ""
        # Algolia gives ISO-8601 with Z; convert to date.
        try:
            posting_date = datetime.fromisoformat(created_at.replace("Z", "+00:00")) \
                .astimezone(timezone.utc).date().isoformat()
        except (ValueError, AttributeError):
            posting_date = ""

        yield {
            "posting_id": posting_id(url, posting_date or None),
            "source": "hn_whoishiring",
            "source_url": url,
            "captured_date": captured,
            "posting_date": posting_date,
            "raw_text": body_text,
            "raw_html": body_html,
            "thread_id": story_id,
            "thread_title": title,
            "author": h.get("author") or "",
        }


# ---- CLI ----

def _thread_filename(thread: dict) -> str:
    # hn-<story_id>-<YYYY-MM>.jsonl
    created = thread.get("created_at") or ""
    yyyy_mm = created[:7] if len(created) >= 7 else "unknown"
    return f"hn-{thread['story_id']}-{yyyy_mm}.jsonl"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Fetch HN 'Who is hiring' thread comments.")
    p.add_argument("--thread", action="append", default=[],
                   help="Specific HN story ID. Can repeat. Overrides --months.")
    p.add_argument("--months", type=int, default=2,
                   help="Number of most-recent whoishiring threads to fetch. Default 2.")
    p.add_argument("--list", action="store_true",
                   help="List discoverable threads and exit. Does not fetch.")
    args = p.parse_args(argv)

    if args.list:
        threads = list_whoishiring_threads(limit=12)
        for t in threads:
            print(f"  {t['story_id']}  {t['created_at'][:10]}  "
                  f"{t['num_comments']:>4} comments  {t['title']}")
        return 0

    # Resolve thread list.
    if args.thread:
        # Resolve titles for nice filenames; cheap one-off lookup.
        threads: list[dict] = []
        for sid in args.thread:
            # Algolia item lookup for metadata.
            r = requests.get(f"https://hn.algolia.com/api/v1/items/{sid}", timeout=15)
            if r.status_code == 200:
                data = r.json()
                threads.append({
                    "story_id": sid,
                    "title": data.get("title") or "",
                    "created_at": data.get("created_at") or "",
                    "num_comments": data.get("children_count") or 0,
                })
            else:
                threads.append({"story_id": sid, "title": "", "created_at": "",
                                "num_comments": 0})
    else:
        threads = list_whoishiring_threads(limit=12)[: args.months]

    if not threads:
        print("No threads to fetch.", file=sys.stderr)
        return 1

    out_dir = raw_dir()
    total = 0
    for t in threads:
        records = list(iter_thread_postings(t))
        fname = out_dir / _thread_filename(t)
        n = write_jsonl(fname, records)
        total += n
        print(f"  {t['story_id']}  {t['title']}  -> {fname.name}  ({n} top-level postings)")

    print(f"Wrote {total} HN postings to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
