#!/usr/bin/env python3
"""
Fetch accepted papers from a conference and write them to a CSV.

Supports ICLR, ICML, and NeurIPS via the OpenReview APIs. Conference-years
that aren't on OpenReview (ICML 2020-2022 and NeurIPS 2020) need a different
source — see ALT_SOURCES below.

Usage:
    python src/fetch.py iclr 2026
    python src/fetch.py neurips 2024
    python src/fetch.py icml 2025
"""

import argparse
from pathlib import Path

import openreview
import openreview.api as openreview_v2
import pandas as pd

DATA_ROOT = Path(__file__).resolve().parent.parent / "data"

# Verified by direct API probe (see memory/openreview-conference-mapping.md).
# Format: (conference, year) -> (api_version, invitation_suffix)
SOURCES = {
    # ICLR — v1 through 2023, v2 from 2024
    ("iclr", 2020): ("v1", "-/Blind_Submission"),
    ("iclr", 2021): ("v1", "-/Blind_Submission"),
    ("iclr", 2022): ("v1", "-/Blind_Submission"),
    ("iclr", 2023): ("v1", "-/Blind_Submission"),
    ("iclr", 2024): ("v2", "-/Submission"),
    ("iclr", 2025): ("v2", "-/Submission"),
    ("iclr", 2026): ("v2", "-/Submission"),
    # ICML — only on OpenReview starting 2023
    ("icml", 2023): ("v2", "-/Submission"),
    ("icml", 2024): ("v2", "-/Submission"),
    ("icml", 2025): ("v2", "-/Submission"),
    # NeurIPS — v1 through 2022, v2 from 2023
    ("neurips", 2021): ("v1", "-/Blind_Submission"),
    ("neurips", 2022): ("v1", "-/Blind_Submission"),
    ("neurips", 2023): ("v2", "-/Submission"),
    ("neurips", 2024): ("v2", "-/Submission"),
    ("neurips", 2025): ("v2", "-/Submission"),
}

ALT_SOURCES = {
    ("icml", 2020): "PMLR v119 (https://proceedings.mlr.press/v119/)",
    ("icml", 2021): "PMLR v139 (https://proceedings.mlr.press/v139/)",
    ("icml", 2022): "PMLR v162 (https://proceedings.mlr.press/v162/)",
    ("neurips", 2020): "https://papers.nips.cc/paper_files/paper/2020",
}

VENUE_ID_NAME = {"iclr": "ICLR", "icml": "ICML", "neurips": "NeurIPS"}

# Strings indicating the paper was not actually accepted.
REJECT_MARKERS = ("Rejected", "Withdrawn", "Desk_Rejected", "Desk-Reject")


def get_value(field):
    """Extract a value from a content field, handling v1 (raw) and v2 ({'value': X})."""
    if isinstance(field, dict) and "value" in field:
        return field["value"]
    return field if field is not None else ""


def fetch_notes(conference: str, year: int, api_ver: str, invitation_suffix: str):
    venue_name = VENUE_ID_NAME[conference]
    invitation = f"{venue_name}.cc/{year}/Conference/{invitation_suffix}"
    if api_ver == "v1":
        client = openreview.Client(baseurl="https://api.openreview.net")
    else:
        client = openreview_v2.OpenReviewClient(baseurl="https://api2.openreview.net")
    print(f"Fetching {invitation} via API {api_ver}...")
    return client.get_all_notes(invitation=invitation)


def row_from_note(note, conference: str, year: int) -> dict | None:
    """Convert a raw note to a CSV row, or None if not an accepted paper."""
    venue   = get_value(note.content.get("venue", "")) or ""
    venueid = get_value(note.content.get("venueid", "")) or ""

    venue_str = f"{venue} {venueid}"
    if any(m in venue_str for m in REJECT_MARKERS):
        return None
    if not venue and not venueid:
        return None  # never assigned a venue → not accepted

    authors    = get_value(note.content.get("authors", []))    or []
    author_ids = get_value(note.content.get("authorids", []))  or []

    return {
        "id":           note.id,
        "conference":   conference,
        "year":         year,
        "title":        get_value(note.content.get("title", "")),
        "authors":      "; ".join(authors) if isinstance(authors, list) else str(authors),
        "author_ids":   "; ".join(author_ids) if isinstance(author_ids, list) else str(author_ids),
        "abstract":     get_value(note.content.get("abstract", "")),
        "keywords":     get_value(note.content.get("keywords", "")),
        "primary_area": get_value(note.content.get("primary_area", "")),
        "venue":        venue,
        "tldr":         get_value(note.content.get("TLDR", "")),
        "url":          f"https://openreview.net/forum?id={note.id}",
        "pdf_url":      f"https://openreview.net/pdf?id={note.id}",
    }


def fetch(conference: str, year: int) -> pd.DataFrame:
    key = (conference, year)
    if key in ALT_SOURCES:
        raise NotImplementedError(
            f"{conference.upper()} {year} is not on OpenReview. "
            f"Fetch from: {ALT_SOURCES[key]}"
        )
    if key not in SOURCES:
        raise ValueError(
            f"Unknown conference/year: {conference} {year}. "
            f"Supported on OpenReview: {sorted(SOURCES.keys())}. "
            f"Need alternate source: {sorted(ALT_SOURCES.keys())}."
        )

    api_ver, suffix = SOURCES[key]
    notes = fetch_notes(conference, year, api_ver, suffix)
    print(f"Got {len(notes)} raw notes; filtering for accepted papers...")

    rows = [r for r in (row_from_note(n, conference, year) for n in notes) if r is not None]
    print(f"Kept {len(rows)} accepted papers")
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser(
        description="Fetch accepted papers from a conference via OpenReview",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
               "  python src/fetch.py iclr 2026\n"
               "  python src/fetch.py neurips 2024\n"
               "  python src/fetch.py icml 2025 --output /tmp/icml.csv\n"
               "\n"
               "Not on OpenReview (use alternate sources):\n"
               "  ICML 2020-2022 — PMLR\n"
               "  NeurIPS 2020   — papers.nips.cc",
    )
    parser.add_argument("conference", help="iclr, icml, or neurips")
    parser.add_argument("year", type=int)
    parser.add_argument("--data-root", default=str(DATA_ROOT))
    parser.add_argument("--output", help="Override output path (default: data/{conference}/{year}/papers.csv)")
    args = parser.parse_args()

    conference = args.conference.lower()
    df = fetch(conference, args.year)

    out_path = (Path(args.output) if args.output
                else Path(args.data_root) / conference / str(args.year) / "papers.csv")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    print(f"Saved {len(df)} papers to {out_path}")


if __name__ == "__main__":
    main()
