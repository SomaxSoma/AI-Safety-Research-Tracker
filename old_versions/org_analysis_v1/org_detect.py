#!/usr/bin/env python3
"""
Detect AI-safety-organisation affiliations in conference papers by reading each
PDF's affiliation block (first page) and acknowledgments section, matching
against ai_safety_orgs.ORGS.

Two goals:
  * tag papers with the safety orgs behind them
  * flag potential LLM false negatives: papers with a safety-ONLY org
    affiliation that DeepSeek marked non-safety

PDFs are streamed into memory, parsed, and discarded — nothing is written to
disk. OpenReview PDFs need auth (env OPENREVIEW_USERNAME / OPENREVIEW_PASSWORD);
PMLR and papers.nips.cc are open. ICML 2026 (icml.cc virtual) has no PDF and is
skipped.

Resumable: appends to data/org_matches.csv and skips ids already there.

Usage:
    OPENREVIEW_USERNAME=... OPENREVIEW_PASSWORD=... \
        python3 src/org_detect.py                 # all conference papers
        python3 src/org_detect.py --safety-only    # only DeepSeek-safety papers
        python3 src/org_detect.py --conference iclr --year 2026
"""

import argparse
import csv
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

import fitz  # pymupdf
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from ai_safety_orgs import find_orgs

OUT = ROOT / "data" / "org_matches.csv"
UA = "Mozilla/5.0 (X11; Linux x86_64) Chrome/120.0 Safari/537.36"
REQUEST_DELAY = 0.5
FIELDNAMES = ["id", "conference", "year", "is_safety", "class", "source",
              "status", "n_pages", "safety_only", "safety_only_aliases",
              "safety_adjacent"]

ACK_RE = re.compile(r"acknowledg", re.IGNORECASE)


def load_papers(conference=None, year=None, safety_only=False) -> pd.DataFrame:
    rows = []
    confs = [conference] if conference else ["iclr", "icml", "neurips"]
    for conf in confs:
        cdir = ROOT / "data" / conf
        if not cdir.exists():
            continue
        for yd in sorted(cdir.iterdir()):
            if year and yd.name != str(year):
                continue
            p, r = yd / "papers.csv", yd / "results.csv"
            if not (p.exists() and r.exists()):
                continue
            pap = pd.read_csv(p, dtype=str)
            res = pd.read_csv(r, dtype=str)
            res["is_safety_b"] = res["is_safety"].astype(str).str.lower().isin(["true", "1"])
            m = pap.merge(res[["id", "is_safety_b", "class"]], on="id", how="left")
            m["conference"] = conf
            m["year"] = yd.name
            rows.append(m)
    df = pd.concat(rows, ignore_index=True)
    if safety_only:
        df = df[df["is_safety_b"] == True]
    return df.reset_index(drop=True)


def get_pdf_bytes(row, orclient) -> tuple[bytes | None, str]:
    """Return (pdf_bytes, source) or (None, reason)."""
    url = str(row.get("pdf_url") or "")
    if "openreview.net" in url:
        if orclient is None:
            return None, "no_auth"
        try:
            return orclient.get_attachment("pdf", id=row["id"]), "openreview"
        except Exception as e:
            return None, f"openreview_err:{str(e)[:40]}"
    if "mlr.press" in url or "nips.cc" in url:
        src = "pmlr" if "mlr.press" in url else "nips.cc"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=90) as resp:
                return resp.read(), src
        except Exception as e:
            return None, f"{src}_err:{str(e)[:40]}"
    return None, "no_pdf_url"


def extract_org_regions(pdf_bytes: bytes) -> tuple[str, int]:
    """Return (affiliation+acknowledgment text, n_pages). We match only these
    regions so risky acronyms (ARC/MATS/FAIR) are trusted where orgs really
    appear, not in body math/prose."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    n = len(doc)
    first_page = doc[0].get_text() if n else ""
    full = "".join(p.get_text() for p in doc)
    doc.close()

    region = first_page  # affiliation block lives on page 1
    m = ACK_RE.search(full)
    if m:
        region += "\n" + full[m.start(): m.start() + 1500]  # acknowledgments window
    return region, n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--conference")
    ap.add_argument("--year")
    ap.add_argument("--safety-only", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    orclient = None
    user, pw = os.environ.get("OPENREVIEW_USERNAME"), os.environ.get("OPENREVIEW_PASSWORD")
    if user and pw:
        import openreview.api as orv2
        orclient = orv2.OpenReviewClient(baseurl="https://api2.openreview.net",
                                         username=user, password=pw)
        print(f"OpenReview authenticated as {user}")
    else:
        print("WARNING: no OpenReview creds — OpenReview PDFs will be skipped")

    df = load_papers(args.conference, args.year, args.safety_only)
    done = set()
    if OUT.exists():
        done = set(pd.read_csv(OUT, dtype=str)["id"])
    todo = df[~df["id"].isin(done)]
    if args.limit:
        todo = todo.head(args.limit)
    print(f"{len(df)} papers selected, {len(done)} already done, {len(todo)} to process")

    write_header = not OUT.exists()
    f = open(OUT, "a", newline="", encoding="utf-8")
    import fcntl
    try:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        sys.exit("Another org_detect process is already writing to org_matches.csv")
    w = csv.DictWriter(f, fieldnames=FIELDNAMES)
    if write_header:
        w.writeheader()

    t0 = time.time()
    n_so = n_done = 0
    for _, row in todo.iterrows():
        pdf, source = get_pdf_bytes(row, orclient)
        rec = {"id": row["id"], "conference": row["conference"], "year": row["year"],
               "is_safety": bool(row["is_safety_b"]), "class": row.get("class", ""),
               "source": source, "status": "", "n_pages": "",
               "safety_only": "", "safety_only_aliases": "", "safety_adjacent": ""}
        if pdf is None:
            rec["status"] = source
        else:
            try:
                region, npages = extract_org_regions(pdf)
                hits = find_orgs(region, affiliation_field=True)
                so = hits["safety_only"]
                sa = hits["safety_adjacent"]
                rec["status"] = "ok"
                rec["n_pages"] = npages
                rec["safety_only"] = "; ".join(so.keys())
                rec["safety_only_aliases"] = "; ".join(
                    f"{k}:{'/'.join(v)}" for k, v in so.items())
                rec["safety_adjacent"] = "; ".join(sa.keys())
                if so:
                    n_so += 1
            except Exception as e:
                rec["status"] = f"parse_err:{str(e)[:40]}"
        w.writerow(rec)
        f.flush()
        n_done += 1
        if source == "openreview" or source.startswith(("pmlr", "nips")):
            time.sleep(REQUEST_DELAY)
        if n_done % 50 == 0:
            rate = n_done / (time.time() - t0)
            eta = (len(todo) - n_done) / rate / 3600 if rate else 0
            print(f"  {n_done}/{len(todo)}  ({rate:.1f}/s, ~{eta:.1f}h left)  "
                  f"safety_only hits so far: {n_so}")

    f.close()
    print(f"\nDone. Processed {n_done}, safety_only-org papers: {n_so}")
    print(f"Output: {OUT}")


if __name__ == "__main__":
    main()
