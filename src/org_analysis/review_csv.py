#!/usr/bin/env python3
"""
Build a human-reviewable CSV of papers with their LLM-confirmed safety-org
associations, so the tagging can be spot-checked by hand.

Columns: title, conference, year, primary_org, primary_funder, orgs, funders,
verdicts (per-candidate affiliation/acknowledgment/mention), url.
orgs and funders are the confirmed associations, split by structural type.

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
        year = int(r["year"])
        conf_all = [o for o in str(r.get("confirmed") or "").split("; ") if o]
        orgs = [o for o in conf_all if org_type(o, year) != "funder"]
        funders = [o for o in conf_all if org_type(o, year) == "funder"]
        rows.append({
            "title": titles.get(r["id"], ""),
            "conference": r["conference"].upper(),
            "year": year,
            "primary_org": r.get("primary_org") or "",
            "primary_funder": r.get("primary_funder") or "",
            "orgs": "; ".join(orgs),
            "funders": "; ".join(funders),
            "candidates": r.get("candidates", ""),
            "verdicts": fmt_verdicts(r.get("verdicts", "")),
            "url": urls.get(r["id"], f"https://openreview.net/forum?id={r['id']}"),
        })
    out = pd.DataFrame(rows).sort_values(["primary_org", "year", "conference"])
    path = ROOT / "data" / "org_review.csv"
    out.to_csv(path, index=False)
    print(f"Wrote {len(out)} papers to {path}")
    print(f"  (with a confirmed org: {(out['orgs'].str.len() > 0).sum()}, "
          f"with a funder: {(out['funders'].str.len() > 0).sum()})")
    print("\nBy primary org:")
    print(out[out['primary_org'] != '']['primary_org'].value_counts().head(15).to_string())


if __name__ == "__main__":
    main()
