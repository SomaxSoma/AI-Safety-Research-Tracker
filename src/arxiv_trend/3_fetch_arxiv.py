#!/usr/bin/env python3
"""
Fetch arXiv ML-cluster abstracts (cs.LG, cs.AI, cs.CL, stat.ML; NOT cs.CV)
month by month via the arXiv API, for a monthly safety-paper trend.

Resumable: writes one CSV per month under data/arxiv/raw/YYYY-MM.csv and skips
months already fetched, so a crash/shutdown only loses the current month.

Usage:
    python src/fetch_arxiv.py                       # 2019-01 .. current month
    python src/fetch_arxiv.py --start 2019-01 --end 2026-06
    python src/fetch_arxiv.py --combine             # just merge raw months -> papers.csv
"""

import argparse
import csv
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
ARXIV_DIR = ROOT / "data" / "arxiv"
RAW_DIR = ARXIV_DIR / "raw"

CATEGORIES = ["cs.LG", "cs.AI", "cs.CL", "stat.ML"]
API_URL = "http://export.arxiv.org/api/query"
PAGE_SIZE = 1000
REQUEST_DELAY = 3.0          # arXiv asks for >= 3s between requests
MAX_RETRIES = 5

NS = {
    "a": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
    "opensearch": "http://a9.com/-/spec/opensearch/1.1/",
}

FIELDNAMES = [
    "id", "title", "abstract", "authors", "primary_category",
    "categories", "published", "updated", "month", "url", "pdf_url",
]


def http_get(url: str) -> str:
    last = None
    for attempt in range(MAX_RETRIES):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "safety-trend-research/1.0"})
            with urllib.request.urlopen(req, timeout=90) as resp:
                return resp.read().decode("utf-8")
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            last = e
            wait = REQUEST_DELAY * (2 ** attempt)
            print(f"    request failed ({e}); retrying in {wait:.0f}s")
            time.sleep(wait)
    raise RuntimeError(f"arXiv request failed after {MAX_RETRIES} tries: {last}")


def month_bounds(y: int, m: int) -> tuple[str, str]:
    start = f"{y:04d}{m:02d}010000"
    if m == 12:
        ny, nm = y + 1, 1
    else:
        ny, nm = y, m + 1
    # end = last minute before next month starts
    end_day = (date(ny, nm, 1) - date(y, m, 1)).days
    end = f"{y:04d}{m:02d}{end_day:02d}2359"
    return start, end


def parse_entry(e, month: str) -> dict | None:
    aid_full = e.find("a:id", NS).text  # e.g. http://arxiv.org/abs/2001.04832v1
    arxiv_id = aid_full.rsplit("/", 1)[-1]
    base_id = arxiv_id.split("v")[0]

    title_el = e.find("a:title", NS)
    summary_el = e.find("a:summary", NS)
    if title_el is None or summary_el is None:
        return None
    title = " ".join(title_el.text.split())
    abstract = " ".join(summary_el.text.split())

    authors = [a.find("a:name", NS).text for a in e.findall("a:author", NS)
               if a.find("a:name", NS) is not None]
    primary = e.find("arxiv:primary_category", NS)
    primary_cat = primary.get("term") if primary is not None else ""
    cats = [c.get("term") for c in e.findall("a:category", NS)]
    published = (e.find("a:published", NS).text or "")
    updated = (e.find("a:updated", NS).text or "")

    return {
        "id": base_id,
        "title": title,
        "abstract": abstract,
        "authors": "; ".join(authors),
        "primary_category": primary_cat,
        "categories": " ".join(cats),
        "published": published,
        "updated": updated,
        "month": month,
        "url": f"https://arxiv.org/abs/{base_id}",
        "pdf_url": f"https://arxiv.org/pdf/{base_id}",
    }


# arXiv returns HTTP 500 for start offsets beyond ~10k in a single query, so any
# date window with more results than this must be bisected into smaller windows.
SAFE_WINDOW = 9000


def _query_window(start_d: str, end_d: str, month: str, depth: int = 0) -> list[dict]:
    """Fetch all papers submitted in [start_d, end_d], bisecting the time window
    recursively if it holds more than SAFE_WINDOW results (arXiv's deep-page cap)."""
    cat_q = " OR ".join(f"cat:{c}" for c in CATEGORIES)
    query = f"({cat_q}) AND submittedDate:[{start_d} TO {end_d}]"

    # Peek at the total for this window (max_results=1 is cheap).
    peek_url = API_URL + "?" + urllib.parse.urlencode({
        "search_query": query, "start": 0, "max_results": 1,
        "sortBy": "submittedDate", "sortOrder": "ascending",
    })
    root = ET.fromstring(http_get(peek_url))
    tot_el = root.find("opensearch:totalResults", NS)
    total = int(tot_el.text) if tot_el is not None else 0

    if total > SAFE_WINDOW and depth < 8:
        # Bisect the datetime window and recurse on each half.
        fmt = "%Y%m%d%H%M"
        a = datetime.strptime(start_d, fmt)
        b = datetime.strptime(end_d, fmt)
        mid = a + (b - a) / 2
        mid_s = mid.strftime(fmt)
        mid_next = (mid + timedelta(minutes=1)).strftime(fmt)
        print(f"    {month}: window {start_d}-{end_d} has {total} > {SAFE_WINDOW}, bisecting")
        time.sleep(REQUEST_DELAY)
        left = _query_window(start_d, mid_s, month, depth + 1)
        time.sleep(REQUEST_DELAY)
        right = _query_window(mid_next, end_d, month, depth + 1)
        return left + right

    time.sleep(REQUEST_DELAY)
    rows, start = [], 0
    while True:
        url = API_URL + "?" + urllib.parse.urlencode({
            "search_query": query, "start": start, "max_results": PAGE_SIZE,
            "sortBy": "submittedDate", "sortOrder": "ascending",
        })
        xml = http_get(url)
        root = ET.fromstring(xml)
        entries = root.findall("a:entry", NS)
        if not entries:
            break
        for e in entries:
            row = parse_entry(e, month)
            if row is not None:
                rows.append(row)
        start += len(entries)
        print(f"    {month}: window {start_d}-{end_d}: {start}/{total}")
        if start >= total:
            break
        time.sleep(REQUEST_DELAY)
    return rows


def fetch_month(y: int, m: int) -> list[dict]:
    month = f"{y:04d}-{m:02d}"
    start_d, end_d = month_bounds(y, m)
    rows = _query_window(start_d, end_d, month)
    # Bisected windows can overlap by a minute at the split boundary; dedup by id.
    seen, unique = set(), []
    for r in rows:
        if r["id"] not in seen:
            seen.add(r["id"])
            unique.append(r)
    return unique


def write_month(month: str, rows: list[dict]):
    path = RAW_DIR / f"{month}.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDNAMES)
        w.writeheader()
        w.writerows(rows)


def iter_months(start: str, end: str):
    sy, sm = map(int, start.split("-"))
    ey, em = map(int, end.split("-"))
    y, m = sy, sm
    while (y, m) <= (ey, em):
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def combine():
    files = sorted(RAW_DIR.glob("*.csv"))
    if not files:
        print("No raw month files to combine.")
        return
    dfs = [pd.read_csv(f, dtype=str) for f in files]
    df = pd.concat(dfs, ignore_index=True)
    before = len(df)
    df = df.drop_duplicates(subset="id").reset_index(drop=True)
    out = ARXIV_DIR / "papers.csv"
    df.to_csv(out, index=False)
    print(f"Combined {len(files)} months: {before} rows -> {len(df)} unique papers")
    print(f"Saved: {out}")


def main():
    parser = argparse.ArgumentParser(description="Fetch arXiv ML abstracts month by month")
    parser.add_argument("--start", default="2019-01", help="First month YYYY-MM (default 2019-01)")
    today = date.today()
    parser.add_argument("--end", default=f"{today.year:04d}-{today.month:02d}",
                        help="Last month YYYY-MM (default current month)")
    parser.add_argument("--combine", action="store_true",
                        help="Only merge existing raw month files into papers.csv")
    args = parser.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if args.combine:
        combine()
        return

    months = list(iter_months(args.start, args.end))
    print(f"Fetching {len(months)} months ({args.start} .. {args.end}) "
          f"for categories: {', '.join(CATEGORIES)}")
    print("-" * 60)

    total_rows = 0
    for y, m in months:
        month = f"{y:04d}-{m:02d}"
        path = RAW_DIR / f"{month}.csv"
        if path.exists():
            n = sum(1 for _ in open(path)) - 1
            print(f"  {month}: already fetched ({n} rows), skipping")
            total_rows += n
            continue
        print(f"  {month}: fetching...")
        rows = fetch_month(y, m)
        write_month(month, rows)
        total_rows += len(rows)
        print(f"  {month}: saved {len(rows)} rows")
        time.sleep(REQUEST_DELAY)

    print("-" * 60)
    print(f"Done. ~{total_rows} rows across {len(months)} months (pre-dedup).")
    combine()


if __name__ == "__main__":
    main()
