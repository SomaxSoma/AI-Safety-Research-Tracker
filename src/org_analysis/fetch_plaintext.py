#!/usr/bin/env python3
"""
Download each safety paper's PDF, extract the full plaintext, save it to
data/plaintext/<id>.txt, and discard the PDF (streamed in memory, nothing else
written to disk). Run ONCE with OpenReview credentials; afterwards every org
analysis (LLM verification, re-tiering, keyword changes) works offline from the
saved text — no more OpenReview round-trips.

Processes ALL DeepSeek-safety conference papers (sourced from results.csv), so
the downstream org analysis is reproducible over the full set. Resumable: skips
ids whose .txt already exists — so a re-run only fetches what is still missing.

OpenReview is fetched via BOTH APIs: the v2 client (ICLR 2024+, NeurIPS 2023+,
ICML 2024+) with a v1 fallback (ICLR <=2023, NeurIPS 2021-2022). A per
conference-year coverage report is printed at the end; nothing is dropped
silently.

Usage (needs OPENREVIEW_USERNAME / OPENREVIEW_PASSWORD for gated PDFs):
    scripts/run_fetch_plaintext.sh
"""

import argparse
import os
import sys
import time
from collections import defaultdict
from pathlib import Path

import fitz
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
from pdf_fetch import get_pdf_bytes  # OpenReview v2/v1 auth / PMLR / nips

TEXT_DIR = ROOT / "data" / "plaintext"
DELAY = 0.5


def all_safety_papers():
    """Every DeepSeek-safety conference paper with (id, pdf_url, conf, year),
    from results + papers CSVs. Deterministic order (sorted) for reproducibility;
    no dependency on the online keyword run."""
    rows = []
    for conf in ["iclr", "icml", "neurips"]:
        cdir = ROOT / "data" / conf
        if not cdir.exists():
            continue
        for yd in sorted(cdir.iterdir()):
            r, p = yd / "results.csv", yd / "papers.csv"
            if not (r.exists() and p.exists()):
                continue
            res = pd.read_csv(r, dtype=str)
            res = res[res["is_safety"].astype(str).str.lower().isin(["true", "1"])]
            pap = pd.read_csv(p, dtype=str)
            m = res[["id"]].merge(pap[["id", "pdf_url"]], on="id", how="left")
            for _, row in m.iterrows():
                rows.append((row["id"], row.get("pdf_url") or "", conf, yd.name))
    return rows


def make_clients(user, pw):
    """Authenticated (v2, v1) OpenReview clients, or (None, None). Each is built
    independently so one API being down does not disable the other."""
    if not (user and pw):
        return None, None
    v2 = v1 = None
    try:
        import openreview.api as orv2
        v2 = orv2.OpenReviewClient(baseurl="https://api2.openreview.net",
                                   username=user, password=pw)
    except Exception as e:
        print(f"WARNING: v2 OpenReview login failed: {str(e)[:80]}")
    try:
        import openreview
        v1 = openreview.Client(baseurl="https://api.openreview.net",
                               username=user, password=pw)
    except Exception as e:
        print(f"WARNING: v1 OpenReview login failed: {str(e)[:80]}")
    return v2, v1


def coverage_report(papers):
    """Print, per conference-year: total safety papers vs how many now have
    plaintext. Surfaces any remaining gap instead of leaving it silent."""
    total, have = defaultdict(int), defaultdict(int)
    for rid, _url, conf, year in papers:
        total[(conf, year)] += 1
        if (TEXT_DIR / f"{rid}.txt").exists():
            have[(conf, year)] += 1
    print("\nCoverage (plaintext / safety papers) by conference-year:")
    gaps = []
    for key in sorted(total):
        conf, year = key
        h, t = have[key], total[key]
        flag = "" if h == t else f"   <-- MISSING {t - h}"
        if h != t:
            gaps.append((conf, year, t - h))
        print(f"  {conf:8s} {year}:  {h:4d} / {t:<4d}{flag}")
    if gaps:
        print(f"\n{sum(g[2] for g in gaps)} papers still missing across "
              f"{len(gaps)} conference-years. Re-run to retry (resumable), or "
              f"they may be genuinely unavailable.")
    else:
        print("\nFull coverage: every safety paper has plaintext.")


def main():
    argparse.ArgumentParser().parse_args()  # no options: always all safety papers
    TEXT_DIR.mkdir(parents=True, exist_ok=True)

    user, pw = os.environ.get("OPENREVIEW_USERNAME"), os.environ.get("OPENREVIEW_PASSWORD")
    orclient, orclient_v1 = make_clients(user, pw)
    if orclient or orclient_v1:
        print(f"OpenReview authenticated as {user} "
              f"(v2={'ok' if orclient else 'no'}, v1={'ok' if orclient_v1 else 'no'})")
    else:
        print("WARNING: no OpenReview creds — OpenReview PDFs will be skipped")
    fitz.TOOLS.mupdf_display_errors(False)

    papers = all_safety_papers()
    todo = [t for t in papers if not (TEXT_DIR / f"{t[0]}.txt").exists()]
    print(f"{len(papers)} safety papers, {len(papers) - len(todo)} already saved, "
          f"{len(todo)} to fetch")

    t0 = time.time()
    n = saved = 0
    fails = []  # (id, conf, year, reason)
    for rid, url, conf, year in todo:
        pdf, src = get_pdf_bytes({"id": rid, "pdf_url": url}, orclient, orclient_v1)
        n += 1
        if pdf is not None:
            try:
                doc = fitz.open(stream=pdf, filetype="pdf")
                text = "".join(p.get_text() for p in doc)
                doc.close()
                (TEXT_DIR / f"{rid}.txt").write_text(text, encoding="utf-8")
                saved += 1
            except Exception as e:
                fails.append((rid, conf, year, f"parse:{str(e)[:40]}"))
        else:
            fails.append((rid, conf, year, src))
        if src.startswith(("openreview", "pmlr", "nips")):
            time.sleep(DELAY)
        if n % 50 == 0:
            rate = n / (time.time() - t0)
            print(f"  {n}/{len(todo)}  ({rate:.1f}/s, ~{(len(todo)-n)/rate/3600:.1f}h)  "
                  f"saved: {saved}, failed: {len(fails)}")

    print(f"\nThis run: saved {saved}, failed {len(fails)} of {len(todo)} attempted.")
    if fails:
        by_reason = defaultdict(int)
        for _rid, _c, _y, reason in fails:
            by_reason[str(reason).split(":")[0]] += 1
        print("Failure reasons:", dict(by_reason))
        for rid, conf, year, reason in fails[:15]:
            print(f"  FAIL {conf} {year} {rid}: {reason}")
        if len(fails) > 15:
            print(f"  ... and {len(fails) - 15} more")

    coverage_report(papers)
    print(f"\nPlaintext dir: {TEXT_DIR}")


if __name__ == "__main__":
    main()
