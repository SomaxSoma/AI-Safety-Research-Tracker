#!/usr/bin/env python3
"""
Build a human-reviewable CSV of papers with their LLM-confirmed safety-org
associations, so the tagging can be spot-checked by hand.

Columns: title, conference, year, primary_org, primary_type, confirmed_orgs,
verdicts (per-candidate affiliation/acknowledgment/mention), url.

Writes data/org_review.csv. Pass --all to include papers with no confirmed org
too (candidates that were all mentions), for false-positive auditing.
"""

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))  # for org_structure
from org_structure import org_type  # noqa: E402


def title_url_map():
    t, u = {}, {}
    for conf in ["iclr", "icml", "neurips"]:
        cdir = ROOT / "data" / conf
        if not cdir.exists():
            continue
        for yd in sorted(cdir.iterdir()):
            p = yd / "papers.csv"
            if p.exists():
                d = pd.read_csv(p, dtype=str)
                t.update(dict(zip(d["id"], d["title"].fillna(""))))
                u.update(dict(zip(d["id"], d.get("url", pd.Series(dtype=str)).fillna(""))))
    return t, u


def fmt_verdicts(js):
    try:
        d = json.loads(js) if isinstance(js, str) and js.strip() else {}
    except Exception:
        return ""
    return "; ".join(f"{k}={v}" for k, v in d.items())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true",
                    help="also include papers whose candidates were all mentions")
    args = ap.parse_args()

    v = pd.read_csv(ROOT / "data" / "org_verified.csv", dtype=str)
    if not args.all:
        v = v[v["confirmed"].fillna("").str.len() > 0]
    titles, urls = title_url_map()

    rows = []
    for _, r in v.iterrows():
        conf_orgs = [o for o in str(r.get("confirmed") or "").split("; ") if o]
        primary = r.get("primary") or ""
        year = int(r["year"])
        rows.append({
            "title": titles.get(r["id"], ""),
            "conference": r["conference"].upper(),
            "year": year,
            "primary_org": primary,
            "primary_type": org_type(primary, year) if primary else "",
            "confirmed_orgs": "; ".join(conf_orgs),
            "candidates": r.get("candidates", ""),
            "verdicts": fmt_verdicts(r.get("verdicts", "")),
            "url": urls.get(r["id"], f"https://openreview.net/forum?id={r['id']}"),
        })
    out = pd.DataFrame(rows).sort_values(["primary_org", "year", "conference"])
    path = ROOT / "data" / "org_review.csv"
    out.to_csv(path, index=False)
    print(f"Wrote {len(out)} papers to {path}")
    print(f"  (with confirmed org: {(out['confirmed_orgs'].str.len()>0).sum()})")
    print("\nBy primary type:")
    print(out[out['primary_type'] != '']['primary_type'].value_counts().to_string())


if __name__ == "__main__":
    main()
