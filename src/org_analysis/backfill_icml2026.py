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

import difflib
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
NOTE_CACHE = ROOT / "data" / "icml" / "2026" / "openreview_notes.csv"
REJECT_RE = re.compile(r"reject|withdraw|desk", re.I)
FUZZY_CUTOFF = 0.93


def norm(t: str) -> str:
    """Loose title key: lowercase alphanumerics, single-spaced."""
    return re.sub(r"[^a-z0-9]+", " ", str(t).lower()).strip()


def cval(content: dict, key: str):
    """Read a v2 note content field (value-wrapped) or a plain value."""
    v = content.get(key)
    return v.get("value") if isinstance(v, dict) else v


def fetch_notes(client):
    """Every ICML 2026 note this account can read: the venueid-accepted set
    UNIONed with whatever the Submission invitation returns (picks up position /
    oral / other accept tracks that carry a different venueid). Deduped by id."""
    by_id = {}
    for kwargs in ({"content": {"venueid": VENUE}},
                   {"invitation": f"{VENUE}/-/Submission"}):
        try:
            for n in client.get_all_notes(**kwargs):
                by_id[n.id] = n
        except Exception as e:
            print(f"  query {kwargs} failed: {str(e)[:60]}")
    return list(by_id.values())


def main():
    user = os.environ.get("OPENREVIEW_USERNAME")
    pw = os.environ.get("OPENREVIEW_PASSWORD")
    if not (user and pw):
        sys.exit("Set OPENREVIEW_USERNAME / OPENREVIEW_PASSWORD")
    import openreview.api as orv2
    client = orv2.OpenReviewClient(baseurl="https://api2.openreview.net",
                                   username=user, password=pw)
    print(f"authenticated as {user}")

    notes = fetch_notes(client)
    print(f"{len(notes)} ICML 2026 notes fetched (all readable tracks)")
    if not notes:
        sys.exit("No notes found — inspect ICML.cc/2026/Conference on openreview.net.")

    cache = pd.DataFrame([{
        "id": n.id,
        "title": cval(n.content, "title"),
        "venue": cval(n.content, "venue"),
        "venueid": cval(n.content, "venueid"),
        "has_pdf": bool(cval(n.content, "pdf")),
    } for n in notes])
    cache.to_csv(NOTE_CACHE, index=False)
    print(f"cached notes -> {NOTE_CACHE}")
    print("venue labels:", dict(Counter(cache["venue"].fillna("(none)"))))

    # accepted = has a venue label that is not a rejection/withdrawal
    accepted = cache[cache["venue"].notna()
                     & ~cache["venue"].str.contains(REJECT_RE, na=False)]
    print(f"{len(accepted)} accepted notes (venue label, not reject/withdraw)")

    title2id = {}
    for _, r in accepted.iterrows():
        t = norm(r["title"])
        if t and t not in title2id:
            title2id[t] = r["id"]
    acc_titles = list(title2id)

    res = pd.read_csv(RESULTS, dtype=str)
    safe = set(res[res["is_safety"].astype(str).str.lower()
                    .isin(["true", "1"])]["id"])

    df = pd.read_csv(PAPERS, dtype=str)
    new_url, exact, fuzzy, fuzzy_log = [], 0, 0, []
    for _, row in df.iterrows():
        key = norm(row["title"])
        nid = title2id.get(key)
        if nid:
            exact += 1
        elif row["id"] in safe:  # fuzzy only for the papers we actually need
            cand = difflib.get_close_matches(key, acc_titles, n=1, cutoff=FUZZY_CUTOFF)
            if cand:
                nid = title2id[cand[0]]
                fuzzy += 1
                fuzzy_log.append((row["title"], cand[0]))
        if nid:
            new_url.append(f"https://openreview.net/pdf?id={nid}")
        else:
            old = row["pdf_url"]
            new_url.append(old if pd.notna(old) else "")
    df["pdf_url"] = new_url
    df.to_csv(PAPERS, index=False)
    print(f"matched {exact} exact + {fuzzy} fuzzy of {len(df)} papers -> {PAPERS}")

    if fuzzy_log:
        print("\nFuzzy matches (verify these look right):")
        for ours, theirs in fuzzy_log[:20]:
            print(f"  ours : {str(ours)[:75]}\n  OR   : {str(theirs)[:75]}")

    hit = df["pdf_url"].str.contains("openreview", na=False)
    got = df[df["id"].isin(safe) & hit]
    miss = df[df["id"].isin(safe) & ~hit]
    print(f"\nSafety papers with a PDF now: {len(got)}/{len(safe)}  "
          f"({len(miss)} still unmatched)")
    for t in miss["title"].head(15):
        print(f"  UNMATCHED: {str(t)[:80]}")
    if len(miss) > 15:
        print(f"  ...and {len(miss) - 15} more")
    print("\nNext: scripts/run_fetch_plaintext.sh, then scripts/run_org_verify_llm.sh")


if __name__ == "__main__":
    main()
