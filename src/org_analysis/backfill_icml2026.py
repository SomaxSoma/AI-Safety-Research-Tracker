#!/usr/bin/env python3
"""
Backfill OpenReview note ids into data/icml/2026/papers.csv.

ICML 2026 was originally scraped from icml.cc/virtual (abstracts only, no PDFs),
so its rows carry `icml-virtual-*` ids and an empty pdf_url. Now that the
accepted papers (Accept regular / Accept spotlight) are on OpenReview, match them
by title and write the OpenReview pdf_url (openreview.net/pdf?id=<note id>) back
into papers.csv. The existing icml-virtual-* id is KEPT (results.csv keys on it);
only pdf_url is filled, and pdf_fetch.get_pdf_bytes reads the note id from that url.

After this, the standard fetch_plaintext.py downloads the matched ICML 2026 PDFs
like any other OpenReview paper.

Needs OPENREVIEW_USERNAME / OPENREVIEW_PASSWORD. Idempotent (re-running just
re-matches). Prints the match rate for safety papers and lists any misses.
"""

import os
import re
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
VENUE = "ICML.cc/2026/Conference"
PAPERS = ROOT / "data" / "icml" / "2026" / "papers.csv"
RESULTS = ROOT / "data" / "icml" / "2026" / "results.csv"


def norm(t: str) -> str:
    """Loose title key: lowercase alphanumerics, single-spaced."""
    return re.sub(r"[^a-z0-9]+", " ", str(t).lower()).strip()


def cval(content: dict, key: str):
    """Read a v2 note content field (value-wrapped) or a plain value."""
    v = content.get(key)
    return v.get("value") if isinstance(v, dict) else v


def fetch_accepted(client):
    """Accepted ICML 2026 notes (content.venueid == the venue id)."""
    try:
        notes = client.get_all_notes(content={"venueid": VENUE})
    except Exception as e:
        print(f"  venueid query failed ({str(e)[:50]}); falling back to Submission")
        notes = []
    if not notes:  # fall back: all submissions, keep the accepted ones
        allsub = client.get_all_notes(invitation=f"{VENUE}/-/Submission")
        notes = [n for n in allsub if cval(n.content, "venueid") == VENUE]
    return notes


def main():
    user = os.environ.get("OPENREVIEW_USERNAME")
    pw = os.environ.get("OPENREVIEW_PASSWORD")
    if not (user and pw):
        sys.exit("Set OPENREVIEW_USERNAME / OPENREVIEW_PASSWORD")
    import openreview.api as orv2
    client = orv2.OpenReviewClient(baseurl="https://api2.openreview.net",
                                   username=user, password=pw)
    print(f"authenticated as {user}")

    notes = fetch_accepted(client)
    print(f"{len(notes)} accepted ICML 2026 notes on OpenReview")
    if not notes:
        sys.exit("No accepted notes found — the venueid/invitation may differ; "
                 "inspect ICML.cc/2026/Conference on openreview.net.")
    print("venue labels:", dict(Counter(cval(n.content, "venue") for n in notes)))

    title2id, dup = {}, 0
    for n in notes:
        t = norm(cval(n.content, "title"))
        if not t:
            continue
        if t in title2id:
            dup += 1
        else:
            title2id[t] = n.id
    if dup:
        print(f"  ({dup} duplicate titles on OpenReview — kept first)")

    df = pd.read_csv(PAPERS, dtype=str)
    keys = df["title"].map(norm)
    new_url, matched = [], 0
    for key, old in zip(keys, df["pdf_url"]):
        nid = title2id.get(key)
        if nid:
            new_url.append(f"https://openreview.net/pdf?id={nid}")
            matched += 1
        else:
            new_url.append(old if pd.notna(old) else "")
    df["pdf_url"] = new_url
    df.to_csv(PAPERS, index=False)
    print(f"matched {matched}/{len(df)} ICML 2026 papers by title -> {PAPERS}")

    # focus: how many of the SAFETY papers now have a pdf?
    res = pd.read_csv(RESULTS, dtype=str)
    safe = set(res[res["is_safety"].astype(str).str.lower()
                    .isin(["true", "1"])]["id"])
    hit = df["pdf_url"].str.contains("openreview", na=False)
    got = df[df["id"].isin(safe) & hit]
    miss = df[df["id"].isin(safe) & ~hit]
    print(f"\nSafety papers with a PDF now: {len(got)}/{len(safe)}")
    for t in miss["title"].head(12):
        print(f"  UNMATCHED: {str(t)[:80]}")
    if len(miss) > 12:
        print(f"  ...and {len(miss) - 12} more unmatched safety papers")
    if len(miss):
        print("\n(Unmatched = title differs between icml.cc and OpenReview; "
              "re-run after checking, or we can add fuzzy matching.)")
    print("\nNext: scripts/run_fetch_plaintext.sh, then scripts/run_org_verify_llm.sh")


if __name__ == "__main__":
    main()
