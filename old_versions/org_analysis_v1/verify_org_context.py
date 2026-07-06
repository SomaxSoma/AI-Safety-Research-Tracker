#!/usr/bin/env python3
"""
Manual-verification aid: re-fetch a random sample of papers that matched an org,
and print the text around each match with a REGION label, so you can judge
whether the hit is a real association (author affiliation / funding
acknowledgment) or just a citation/mention (e.g. "models like GPT-4 (OpenAI)").

Region heuristic on page 1:
  AUTHOR-BLOCK  first ~700 chars (title + authors + affiliations)
  ABSTRACT/INTRO   rest of page 1  (where labs get *mentioned*, not affiliated)
  ACK           inside the acknowledgments window

Needs OpenReview creds in env (OPENREVIEW_USERNAME / OPENREVIEW_PASSWORD) for
the gated papers; PMLR/nips.cc are open.

Usage:
    scripts/run_org_verify.sh --n 20 --tier adjacent
"""

import argparse
import os
import re
import sys
from pathlib import Path

import fitz
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
from ai_safety_orgs import ORGS, _pattern  # noqa: E402
import org_detect as od  # noqa: E402

AUTHOR_BLOCK_CHARS = 700
ACK_RE = re.compile(r"acknowledg", re.IGNORECASE)


def build_pdfurl_map():
    m = {}
    for conf in ["iclr", "icml", "neurips"]:
        cdir = ROOT / "data" / conf
        if not cdir.exists():
            continue
        for yd in sorted(cdir.iterdir()):
            p = yd / "papers.csv"
            if p.exists():
                d = pd.read_csv(p, dtype=str)
                for _, r in d.iterrows():
                    m[r["id"]] = r.get("pdf_url", "")
    return m


def region_of(pos, page1_len, ack_start):
    if ack_start is not None and pos >= ack_start:
        return "ACK"
    if pos < AUTHOR_BLOCK_CHARS:
        return "AUTHOR-BLOCK"
    if pos < page1_len:
        return "ABSTRACT/INTRO"
    return "BODY"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--tier", choices=["only", "adjacent", "both"], default="both")
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    user, pw = os.environ.get("OPENREVIEW_USERNAME"), os.environ.get("OPENREVIEW_PASSWORD")
    orclient = None
    if user and pw:
        import openreview.api as orv2
        orclient = orv2.OpenReviewClient(baseurl="https://api2.openreview.net",
                                         username=user, password=pw)

    dfm = pd.read_csv(ROOT / "data" / "org_matches.csv", dtype=str)
    ok = dfm[dfm["status"] == "ok"].copy()
    col = {"only": ["safety_only"], "adjacent": ["safety_adjacent"],
           "both": ["safety_only", "safety_adjacent"]}[args.tier]
    mask = False
    for c in col:
        mask = mask | (ok[c].fillna("").str.len() > 0)
    hits = ok[mask].sample(n=min(args.n, mask.sum()), random_state=args.seed)

    urlmap = build_pdfurl_map()
    fitz.TOOLS.mupdf_display_errors(False)

    print(f"Verifying {len(hits)} sampled papers (tier={args.tier})\n" + "=" * 70)
    for _, row in hits.iterrows():
        rid = row["id"]
        orgs = []
        for c in col:
            orgs += [o for o in str(row.get(c) or "").split("; ") if o]
        fake = {"id": rid, "pdf_url": urlmap.get(rid, "")}
        pdf, src = od.get_pdf_bytes(fake, orclient)
        print(f"\n[{row['conference']} {row['year']}] {rid}  (orgs: {', '.join(orgs)})")
        if pdf is None:
            print(f"  could not fetch: {src}")
            continue
        doc = fitz.open(stream=pdf, filetype="pdf")
        page1 = doc[0].get_text() if len(doc) else ""
        full = "".join(p.get_text() for p in doc)
        doc.close()
        am = ACK_RE.search(full)
        region_text = page1 + ("\n" + full[am.start():am.start() + 1500] if am else "")
        ack_start = len(page1) + 1 if am else None

        for org in orgs:
            for alias in ORGS[org]["aliases"]:
                pat = _pattern(alias)
                for m in pat.finditer(region_text):
                    pos = m.start()
                    reg = region_of(pos, len(page1), ack_start)
                    ctx = region_text[max(0, pos - 70): pos + len(alias) + 70]
                    ctx = " ".join(ctx.split())
                    print(f"   {org:28} [{reg:13}] …{ctx}…")
                    break  # first occurrence per alias is enough


if __name__ == "__main__":
    main()
