#!/usr/bin/env python3
"""
Download each safety paper's PDF, extract the full plaintext, save it to
data/plaintext/<id>.txt, and discard the PDF (streamed in memory, nothing else
written to disk). Run ONCE with OpenReview credentials; afterwards every org
analysis (LLM verification, re-tiering, keyword changes) works offline from the
saved text — no more OpenReview round-trips.

Processes ALL DeepSeek-safety conference papers (sourced from results.csv), so
the downstream org analysis is reproducible over the full set. Resumable: skips
ids whose .txt already exists.

Usage (needs OPENREVIEW_USERNAME / OPENREVIEW_PASSWORD for gated PDFs):
    scripts/run_fetch_plaintext.sh
"""

import argparse
import os
import sys
import time
from pathlib import Path

import fitz
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
from pdf_fetch import get_pdf_bytes  # OpenReview auth / PMLR / nips

TEXT_DIR = ROOT / "data" / "plaintext"
DELAY = 0.5


def all_safety_papers():
    """Every DeepSeek-safety conference paper with its pdf_url (from results +
    papers CSVs). Reproducible: no dependency on the online keyword run."""
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
                rows.append((row["id"], row.get("pdf_url") or ""))
    return rows


def main():
    argparse.ArgumentParser().parse_args()  # no options: always all safety papers
    TEXT_DIR.mkdir(parents=True, exist_ok=True)

    user, pw = os.environ.get("OPENREVIEW_USERNAME"), os.environ.get("OPENREVIEW_PASSWORD")
    orclient = None
    if user and pw:
        import openreview.api as orv2
        orclient = orv2.OpenReviewClient(baseurl="https://api2.openreview.net",
                                         username=user, password=pw)
        print(f"OpenReview authenticated as {user}")
    else:
        print("WARNING: no OpenReview creds — OpenReview PDFs will be skipped")
    fitz.TOOLS.mupdf_display_errors(False)

    papers = all_safety_papers()
    todo = [(rid, url) for rid, url in papers if not (TEXT_DIR / f"{rid}.txt").exists()]
    print(f"{len(papers)} safety papers, {len(papers) - len(todo)} already saved, "
          f"{len(todo)} to fetch")

    t0 = time.time(); n = saved = 0
    for rid, url in todo:
        pdf, src = get_pdf_bytes({"id": rid, "pdf_url": url}, orclient)
        n += 1
        if pdf is not None:
            try:
                doc = fitz.open(stream=pdf, filetype="pdf")
                text = "".join(p.get_text() for p in doc)
                doc.close()
                (TEXT_DIR / f"{rid}.txt").write_text(text, encoding="utf-8")
                saved += 1
            except Exception as e:
                print(f"  parse fail {rid}: {str(e)[:50]}")
        if src == "openreview" or src.startswith(("pmlr", "nips")):
            time.sleep(DELAY)
        if n % 50 == 0:
            rate = n / (time.time() - t0)
            print(f"  {n}/{len(todo)}  ({rate:.1f}/s, ~{(len(todo)-n)/rate/3600:.1f}h)  saved: {saved}")

    print(f"\nDone. Saved {saved} plaintext files to {TEXT_DIR}")


if __name__ == "__main__":
    main()
