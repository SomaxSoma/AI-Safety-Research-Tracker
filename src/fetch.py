#!/usr/bin/env python3
"""
Fetch accepted papers from a conference and write them to a CSV.

Supports ICLR, ICML, and NeurIPS via three sources:
  - OpenReview v1 (ICLR 2020-2023, NeurIPS 2021-2022)
  - OpenReview v2 (ICLR 2024+, ICML 2023+, NeurIPS 2023+)
  - PMLR scraping (ICML 2020-2022)
  - papers.nips.cc scraping (NeurIPS 2020)

All sources produce the same CSV schema:
  id, conference, year, title, authors, author_ids, abstract,
  keywords, primary_area, venue, tldr, url, pdf_url

Usage:
    python src/fetch.py iclr 2026
    python src/fetch.py icml 2020       # uses PMLR
    python src/fetch.py neurips 2020    # uses papers.nips.cc
"""

import argparse
import html as html_module
import re
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import openreview
import openreview.api as openreview_v2
import pandas as pd

DATA_ROOT = Path(__file__).resolve().parent.parent / "data"
USER_AGENT = "Mozilla/5.0 (iclr2026-ai-safety research tracker)"

# Verified by direct API probe (see memory/openreview-conference-mapping.md).
# Format: (conference, year) -> (api_version, invitation_suffix)
OPENREVIEW_SOURCES = {
    ("iclr", 2020): ("v1", "-/Blind_Submission"),
    ("iclr", 2021): ("v1", "-/Blind_Submission"),
    ("iclr", 2022): ("v1", "-/Blind_Submission"),
    ("iclr", 2023): ("v1", "-/Blind_Submission"),
    ("iclr", 2024): ("v2", "-/Submission"),
    ("iclr", 2025): ("v2", "-/Submission"),
    ("iclr", 2026): ("v2", "-/Submission"),
    ("icml", 2023): ("v2", "-/Submission"),
    ("icml", 2024): ("v2", "-/Submission"),
    ("icml", 2025): ("v2", "-/Submission"),
    ("neurips", 2021): ("v1", "-/Blind_Submission"),
    ("neurips", 2022): ("v1", "-/Blind_Submission"),
    ("neurips", 2023): ("v2", "-/Submission"),
    ("neurips", 2024): ("v2", "-/Submission"),
    ("neurips", 2025): ("v2", "-/Submission"),
}

PMLR_VOLUMES = {
    ("icml", 2020): "v119",
    ("icml", 2021): "v139",
    ("icml", 2022): "v162",
}

PAPERS_NIPS_YEARS = {2020}

VENUE_ID_NAME = {"iclr": "ICLR", "icml": "ICML", "neurips": "NeurIPS"}
REJECT_MARKERS = ("Rejected", "Withdrawn", "Desk_Rejected", "Desk-Reject")

EMPTY_ROW = {
    "keywords": "", "primary_area": "", "tldr": "",
}


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def http_get(url: str, retries: int = 3) -> str:
    """GET with retries and a polite UA."""
    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            last_err = e
            time.sleep(2 ** attempt)
    raise RuntimeError(f"Failed to fetch {url}: {last_err}")


def strip_html(s: str) -> str:
    """Remove HTML tags and decode entities, collapsing whitespace."""
    s = re.sub(r"<[^>]+>", " ", s)
    s = html_module.unescape(s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


# ---------------------------------------------------------------------------
# OpenReview source
# ---------------------------------------------------------------------------

def or_get_value(field):
    if isinstance(field, dict) and "value" in field:
        return field["value"]
    return field if field is not None else ""


def fetch_openreview_notes(conference: str, year: int, api_ver: str, suffix: str):
    venue_name = VENUE_ID_NAME[conference]
    invitation = f"{venue_name}.cc/{year}/Conference/{suffix}"
    if api_ver == "v1":
        client = openreview.Client(baseurl="https://api.openreview.net")
    else:
        client = openreview_v2.OpenReviewClient(baseurl="https://api2.openreview.net")
    print(f"Fetching {invitation} via OpenReview {api_ver}...")
    return client.get_all_notes(invitation=invitation)


def row_from_or_note(note, conference: str, year: int) -> dict | None:
    venue   = or_get_value(note.content.get("venue", "")) or ""
    venueid = or_get_value(note.content.get("venueid", "")) or ""
    venue_str = f"{venue} {venueid}"
    if any(m in venue_str for m in REJECT_MARKERS):
        return None
    if not venue and not venueid:
        return None

    authors    = or_get_value(note.content.get("authors", []))    or []
    author_ids = or_get_value(note.content.get("authorids", []))  or []

    return {
        "id":           note.id,
        "conference":   conference,
        "year":         year,
        "title":        or_get_value(note.content.get("title", "")),
        "authors":      "; ".join(authors) if isinstance(authors, list) else str(authors),
        "author_ids":   "; ".join(author_ids) if isinstance(author_ids, list) else str(author_ids),
        "abstract":     or_get_value(note.content.get("abstract", "")),
        "keywords":     or_get_value(note.content.get("keywords", "")),
        "primary_area": or_get_value(note.content.get("primary_area", "")),
        "venue":        venue,
        "tldr":         or_get_value(note.content.get("TLDR", "")),
        "url":          f"https://openreview.net/forum?id={note.id}",
        "pdf_url":      f"https://openreview.net/pdf?id={note.id}",
    }


def fetch_openreview(conference: str, year: int) -> list[dict]:
    api_ver, suffix = OPENREVIEW_SOURCES[(conference, year)]
    notes = fetch_openreview_notes(conference, year, api_ver, suffix)
    print(f"Got {len(notes)} raw notes; filtering for accepted papers...")
    return [r for r in (row_from_or_note(n, conference, year) for n in notes) if r is not None]


# ---------------------------------------------------------------------------
# PMLR source (ICML 2020-2022)
# ---------------------------------------------------------------------------

PMLR_PAPER_DIV_RE = re.compile(
    r'<div class="paper">\s*'
    r'<p class="title">(?P<title>.*?)</p>\s*'
    r'<p class="details">\s*'
    r'<span class="authors">(?P<authors>.*?)</span>'
    r'.*?'
    r'<p class="links">(?P<links>.*?)</p>',
    re.DOTALL,
)
PMLR_LINK_RE = re.compile(r'href="(?P<href>[^"]+)"[^>]*>(?P<label>[^<]+)</a>')


def parse_pmlr_index(html: str, conference: str, year: int, volume: str) -> list[dict]:
    """Parse a PMLR volume index page into a list of partial paper records."""
    papers = []
    for match in PMLR_PAPER_DIV_RE.finditer(html):
        title = strip_html(match.group("title"))
        # Authors are separated by &nbsp;,
        authors_raw = strip_html(match.group("authors"))
        authors = [a.strip() for a in authors_raw.split(",") if a.strip()]

        # Extract abs URL and PDF URL
        abs_url, pdf_url = "", ""
        for link in PMLR_LINK_RE.finditer(match.group("links")):
            href = link.group("href")
            label = link.group("label").strip().lower()
            if label == "abs":
                abs_url = href
            elif label == "download pdf":
                pdf_url = href

        if not abs_url:
            continue

        # The paper "id" is the slug before .html in abs_url (e.g. "abbas20a")
        slug = abs_url.rsplit("/", 1)[-1].rsplit(".", 1)[0]

        papers.append({
            "id":           f"pmlr-{volume}-{slug}",
            "conference":   conference,
            "year":         year,
            "title":        title,
            "authors":      "; ".join(authors),
            "author_ids":   "",  # PMLR has no stable author IDs
            "abstract":     "",  # filled in by per-paper fetch
            "venue":        f"{VENUE_ID_NAME[conference]} {year}",
            "url":          abs_url,
            "pdf_url":      pdf_url,
            **EMPTY_ROW,
        })
    return papers


PMLR_ABSTRACT_RE = re.compile(
    r'<div[^>]*class="abstract"[^>]*>(.*?)</div>',
    re.DOTALL | re.IGNORECASE,
)


def fetch_pmlr_abstract(url: str) -> str:
    html = http_get(url)
    m = PMLR_ABSTRACT_RE.search(html)
    return strip_html(m.group(1)) if m else ""


def fetch_pmlr(conference: str, year: int, workers: int = 20) -> list[dict]:
    volume = PMLR_VOLUMES[(conference, year)]
    index_url = f"https://proceedings.mlr.press/{volume}/"
    print(f"Fetching PMLR index {index_url}...")
    index_html = http_get(index_url)
    papers = parse_pmlr_index(index_html, conference, year, volume)
    print(f"Found {len(papers)} papers on PMLR {volume}, fetching abstracts ({workers} workers)...")

    def enrich(i_paper):
        i, paper = i_paper
        try:
            paper["abstract"] = fetch_pmlr_abstract(paper["url"])
        except Exception as e:
            print(f"  ! abstract fetch failed for {paper['id']}: {e}")
        return i, paper

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for n, (i, p) in enumerate(pool.map(enrich, enumerate(papers)), 1):
            papers[i] = p
            if n % 100 == 0:
                print(f"  {n}/{len(papers)} abstracts fetched")
    return papers


# ---------------------------------------------------------------------------
# papers.nips.cc source (NeurIPS 2020 and earlier)
# ---------------------------------------------------------------------------

NIPS_LINK_RE = re.compile(
    r'<a\s+title="paper title"\s+href="(?P<href>/paper[^"]+)"[^>]*>(?P<title>[^<]+)</a>'
)
NIPS_TITLE_RE = re.compile(r'<h1 class="paper-title">(?P<t>.*?)</h1>', re.DOTALL)
NIPS_AUTHORS_RE = re.compile(r'<p class="paper-authors">(?P<a>.*?)</p>', re.DOTALL)
NIPS_ABSTRACT_RE = re.compile(r'<p class="paper-abstract">(?P<x>.*?)</p>\s*</section>', re.DOTALL)


def parse_nips_index(html: str) -> list[tuple[str, str]]:
    """Parse the year-index page into (relative_url, title) tuples."""
    return [(m.group("href"), strip_html(m.group("title")))
            for m in NIPS_LINK_RE.finditer(html)]


def fetch_nips_paper(rel_url: str, conference: str, year: int) -> dict:
    base = "https://papers.nips.cc"
    abs_url = base + rel_url
    page = http_get(abs_url)

    title = NIPS_TITLE_RE.search(page)
    authors = NIPS_AUTHORS_RE.search(page)
    abstract = NIPS_ABSTRACT_RE.search(page)

    # The unique hash in the URL is the paper ID.
    # rel_url example: /paper_files/paper/2020/hash/0004d0...-Abstract.html
    hash_match = re.search(r"/hash/([0-9a-f]+)-Abstract\.html", rel_url)
    paper_hash = hash_match.group(1) if hash_match else rel_url.rsplit("/", 1)[-1]

    pdf_url = ""
    if hash_match:
        pdf_url = f"{base}/paper_files/paper/{year}/file/{paper_hash}-Paper.pdf"

    authors_str = ""
    if authors:
        # paper-authors text is usually a comma-separated list
        raw = strip_html(authors.group("a"))
        author_list = [a.strip() for a in raw.split(",") if a.strip()]
        authors_str = "; ".join(author_list)

    return {
        "id":           f"nips-{year}-{paper_hash}",
        "conference":   conference,
        "year":         year,
        "title":        strip_html(title.group("t")) if title else "",
        "authors":      authors_str,
        "author_ids":   "",
        "abstract":     strip_html(abstract.group("x")) if abstract else "",
        "venue":        f"NeurIPS {year}",
        "url":          abs_url,
        "pdf_url":      pdf_url,
        **EMPTY_ROW,
    }


def fetch_nips(year: int, workers: int = 20) -> list[dict]:
    index_url = f"https://papers.nips.cc/paper_files/paper/{year}"
    print(f"Fetching NeurIPS index {index_url}...")
    index_html = http_get(index_url)
    entries = parse_nips_index(index_html)
    print(f"Found {len(entries)} papers, fetching detail pages ({workers} workers)...")

    papers = [None] * len(entries)

    def fetch_one(i_url):
        i, (rel_url, _) = i_url
        try:
            return i, fetch_nips_paper(rel_url, "neurips", year)
        except Exception as e:
            print(f"  ! fetch failed for {rel_url}: {e}")
            return i, None

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for n, (i, paper) in enumerate(pool.map(fetch_one, enumerate(entries)), 1):
            if paper is not None:
                papers[i] = paper
            if n % 100 == 0:
                print(f"  {n}/{len(entries)} papers fetched")

    return [p for p in papers if p is not None]


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

def fetch(conference: str, year: int, workers: int = 20) -> pd.DataFrame:
    key = (conference, year)
    if key in OPENREVIEW_SOURCES:
        rows = fetch_openreview(conference, year)
    elif key in PMLR_VOLUMES:
        rows = fetch_pmlr(conference, year, workers=workers)
    elif conference == "neurips" and year in PAPERS_NIPS_YEARS:
        rows = fetch_nips(year, workers=workers)
    else:
        raise ValueError(
            f"Unknown conference/year: {conference} {year}. "
            f"OpenReview: {sorted(OPENREVIEW_SOURCES.keys())}. "
            f"PMLR: {sorted(PMLR_VOLUMES.keys())}. "
            f"NeurIPS proceedings: {sorted(('neurips', y) for y in PAPERS_NIPS_YEARS)}."
        )
    print(f"Kept {len(rows)} accepted papers")
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser(
        description="Fetch accepted papers from a conference",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
               "  python src/fetch.py iclr 2026          # OpenReview\n"
               "  python src/fetch.py icml 2020          # PMLR\n"
               "  python src/fetch.py neurips 2020       # papers.nips.cc\n",
    )
    parser.add_argument("conference", help="iclr, icml, or neurips")
    parser.add_argument("year", type=int)
    parser.add_argument("--data-root", default=str(DATA_ROOT))
    parser.add_argument("--output", help="Override output path")
    parser.add_argument("--workers", type=int, default=20,
                        help="Parallel HTTP workers for PMLR/NeurIPS scraping (default: 20)")
    args = parser.parse_args()

    conference = args.conference.lower()
    df = fetch(conference, args.year, workers=args.workers)

    out_path = (Path(args.output) if args.output
                else Path(args.data_root) / conference / str(args.year) / "papers.csv")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    print(f"Saved {len(df)} papers to {out_path}")


if __name__ == "__main__":
    main()
