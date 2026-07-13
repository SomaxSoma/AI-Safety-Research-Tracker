#!/usr/bin/env python3
"""
LLM second pass to confirm org ASSOCIATION (affiliation / acknowledgment) vs
mere MENTION/citation ("hosted on Hugging Face", "models like GPT-4").

Single "safety org" class (no more safety-only vs safety-adjacent split):
  all independent safety orgs/funders/programs from ai_safety_orgs.ORGS
  + OpenAI, Anthropic, Google DeepMind
  - all other general-purpose labs (Meta, Hugging Face, Microsoft, Scale, Mila,
    Vector, AI2, Cohere, Shanghai, xAI, EleutherAI) are dropped.

For each safety paper that had a keyword hit (from data/org_matches.csv), it
re-fetches the PDF, pulls the text windows around each matched org name, and asks
the LLM to classify each org's relationship to the paper. Keeps only
affiliation/acknowledgment.

Needs OPENREVIEW_USERNAME / OPENREVIEW_PASSWORD (gated PDFs) and
OPENROUTER_API_KEY (the LLM). Resumable: appends to data/org_verified.csv.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

import pandas as pd
from openai import OpenAI

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))  # for org_structure
sys.path.insert(0, str(ROOT))
from ai_safety_orgs import ORGS, _pattern, find_orgs  # noqa: E402
from org_structure import SAFETY_ORGS, org_type  # noqa: E402

INDEP = "University/Independent/other"


def category_tag(org):
    """company / funder / safety org-program — tells the LLM which primary rule
    applies. Year-invariant for this purpose (OpenAI is a company either way)."""
    t = org_type(org, 2026)
    if t == "funder":
        return "funder"
    if t in ("PBC", "corporate"):
        return "company"
    return "safety org/program"

OUT = ROOT / "data" / "org_verified.csv"
MODEL = "deepseek/deepseek-v4-flash"
HEADER = 3000      # chars of front matter (title/authors/affiliations/abstract)
ACK = 1800         # chars of the acknowledgments window
ACK_RE = re.compile(r"acknowledg", re.IGNORECASE)

PROMPT = """You are determining which organizations are genuinely BEHIND a research paper (versus merely mentioned/cited), and which single organization the paper is PRIMARILY from.

Each snippet below is from a paper's first page (title/authors/affiliations/abstract/intro) and its acknowledgments. Every organization is tagged [company], [safety org/program], or [funder].

STEP 1 — classify each organization's relationship to THIS paper:
- "affiliation": an author's listed institution or employer
- "acknowledgment": a funder, grant, program, fellowship, or mentorship thanked (compute, funding, advising)
- "mention": only cited, compared against, or used as a tool/platform/dataset host (e.g. "available on Hugging Face", "models like GPT-4")
- "absent": not really about this organization

STEP 2 — pick the single PRIMARY organization the research is *from* (who organized/led it). Consider only orgs you marked "affiliation" or "acknowledgment", and apply:
- [safety org/program] (e.g. MATS, SPAR, Apart, Redwood, safety centres, government safety institutes): these HOST/ORGANIZE the research even when the authors are based at various universities and the org appears only in acknowledgments/mentorship. Prefer them as primary. Example: a paper by PhD students at universities, done through the MATS program with a mentor at Anthropic, is primarily MATS — not Anthropic, not the universities.
- [company] (e.g. Google DeepMind, OpenAI, Anthropic, Google, Meta, startups): choose a company as primary ONLY if the work is actually led by it — most or a clear plurality of the authors are affiliated with that company, or it is evidently a company project. If only one or a couple of company authors appear among many university authors, the company is NOT primary; that author merely happens to work there.
- Otherwise — no [safety org/program] organizes it and no [company] clearly leads it (a lone company author among academics, or authors only at universities / independent / not listed) — set primary to "University/Independent/other".

STEP 3 — pick the single PRIMARY funder among the [funder] orgs you marked "acknowledgment" (the main grant/philanthropic backer), or null. A [funder] is NEVER the primary organization.

Return ONLY a JSON object:
{"verdicts": {"<org>": "affiliation|acknowledgment|mention|absent", ...}, "primary_org": "<org name or 'University/Independent/other'>", "primary_funder": "<funder name or null>"}"""


def _clean(s):
    s = (s or "").strip()
    return "" if s.lower() in ("null", "none", "") else s


def verify_paper(client, region_text, orgs):
    """Return (verdicts, primary_org_raw, primary_funder_raw). Raw = the LLM's
    picks before validation against the confirmed set (done by resolve_primary).
    The LLM gets the whole front-matter+acknowledgments region (so it can see the
    full author list) plus the tagged list of keyword-matched candidate orgs."""
    if not orgs:
        return {}, "", ""
    tagged = "\n".join(f'- "{o}" [{category_tag(o)}]' for o in orgs)
    user = (PROMPT + "\n\nCandidate organizations (keyword-matched in this paper):\n"
            + tagged + "\n\nPaper text (front matter + acknowledgments):\n"
            + region_text)
    for attempt in range(3):
        try:
            r = client.chat.completions.create(
                model=MODEL, temperature=0.0,
                messages=[{"role": "user", "content": user}])
            txt = r.choices[0].message.content.strip()
            if txt.startswith("```"):
                txt = "\n".join(txt.split("\n")[1:-1])
            start, end = txt.find("{"), txt.rfind("}") + 1
            data = json.loads(txt[start:end])
            return (data.get("verdicts", {}),
                    _clean(data.get("primary_org")),
                    _clean(data.get("primary_funder")))
        except Exception:
            continue
    return {}, "", ""


def resolve_primary(cands, verdicts, p_org_raw, p_funder_raw):
    """Validate the LLM's primary picks against the confirmed set. Returns
    (confirmed, primary_org, primary_funder). primary_org is a confirmed research
    org, INDEP, or "" (no confirmed org). A funder-only paper is INDEP."""
    confirmed = [o for o in cands if verdicts.get(o) in ("affiliation", "acknowledgment")]
    research = [o for o in confirmed if category_tag(o) != "funder"]
    funders = [o for o in confirmed if category_tag(o) == "funder"]

    if not confirmed:
        p_org = ""
    elif not research:               # funded, but no research org -> independent
        p_org = INDEP
    elif p_org_raw in research:      # LLM named a valid research org
        p_org = p_org_raw
    else:                            # LLM said independent (or anything invalid)
        p_org = INDEP

    p_funder = p_funder_raw if p_funder_raw in funders else (funders[0] if funders else "")
    return confirmed, p_org, p_funder


def candidates_in(region_text):
    """Keyword-match the retained safety orgs on the affiliation region."""
    hits = find_orgs(region_text, affiliation_field=True)
    found = list(hits["safety_only"]) + list(hits["safety_adjacent"])
    return [o for o in found if o in SAFETY_ORGS]


def safety_paper_years():
    """id -> (conference, year) for every DeepSeek-safety conference paper."""
    m = {}
    for conf in ["iclr", "icml", "neurips"]:
        cdir = ROOT / "data" / conf
        if not cdir.exists():
            continue
        for yd in sorted(cdir.iterdir()):
            r = yd / "results.csv"
            if r.exists():
                d = pd.read_csv(r, dtype=str)
                d = d[d["is_safety"].astype(str).str.lower().isin(["true", "1"])]
                for pid in d["id"]:
                    m[pid] = (conf, yd.name)
    return m


FIELDS = ["id", "conference", "year", "candidates", "confirmed",
          "primary_org", "primary_funder", "verdicts"]


def region_of(full):
    """Front matter (all authors + affiliations + abstract) plus the
    acknowledgments window — enough for the LLM to see the whole author list and
    judge which org actually leads the work."""
    region = full[:HEADER]
    am = ACK_RE.search(full)
    if am:
        region += "\n\n[Acknowledgments]\n" + full[am.start():am.start() + ACK]
    return region


def process_paper(rid, conf, year, llm, TEXT_DIR):
    """Full LLM pass for one paper -> row dict (new schema) + made_llm_call."""
    full = (TEXT_DIR / f"{rid}.txt").read_text(encoding="utf-8", errors="replace")
    cands = candidates_in(region_of(full))
    confirmed, p_org, p_funder, verdicts, made = [], "", "", {}, False
    if cands:  # only papers with a candidate cost an LLM call
        verdicts, p_org_raw, p_funder_raw = verify_paper(llm, region_of(full), cands)
        confirmed, p_org, p_funder = resolve_primary(cands, verdicts, p_org_raw, p_funder_raw)
        made = True
    return {"id": rid, "conference": conf, "year": year,
            "candidates": "; ".join(cands), "confirmed": "; ".join(confirmed),
            "primary_org": p_org, "primary_funder": p_funder,
            "verdicts": json.dumps(verdicts)}, made


def reverify(llm, TEXT_DIR, meta):
    """Re-run the LLM only on papers that already have a confirmed org (to apply
    the new primary rules) and migrate the rest to the new schema. Rewrites
    org_verified.csv (backing up the old one first)."""
    prev = pd.read_csv(OUT, dtype=str).fillna("")
    bak = OUT.with_suffix(".csv.bak")
    prev.to_csv(bak, index=False)
    todo = prev[prev["confirmed"].str.len() > 0]
    print(f"{len(prev)} rows, re-running {len(todo)} with a confirmed org "
          f"(backup: {bak})")
    rows, n_llm = [], 0
    for _, r in prev.iterrows():
        rid = r["id"]
        if r["confirmed"].strip() and (TEXT_DIR / f"{rid}.txt").exists():
            row, _ = process_paper(rid, r["conference"], r["year"], llm, TEXT_DIR)
            n_llm += 1
            if n_llm % 25 == 0:
                print(f"  reverified {n_llm}/{len(todo)}")
        else:  # no confirmed org -> just migrate columns, no LLM
            row = {"id": rid, "conference": r["conference"], "year": r["year"],
                   "candidates": r.get("candidates", ""), "confirmed": r["confirmed"],
                   "primary_org": "", "primary_funder": "", "verdicts": r.get("verdicts", "")}
        rows.append(row)
    pd.DataFrame(rows)[FIELDS].to_csv(OUT, index=False)
    print(f"\nDone. Reverified {n_llm} papers. Output: {OUT}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reverify", action="store_true",
                    help="re-run the LLM on papers that already have a confirmed "
                         "org (new primary rules), migrate the rest, rewrite the CSV")
    args = ap.parse_args()

    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        sys.exit("Set OPENROUTER_API_KEY")
    llm = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=key)
    TEXT_DIR = ROOT / "data" / "plaintext"
    if not TEXT_DIR.exists():
        sys.exit(f"No plaintext found at {TEXT_DIR}. Run fetch_plaintext.py first.")
    meta = safety_paper_years()

    if args.reverify:
        if not OUT.exists():
            sys.exit(f"No {OUT} to reverify.")
        reverify(llm, TEXT_DIR, meta)
        return

    ids = sorted(p.stem for p in TEXT_DIR.glob("*.txt") if p.stem in meta)
    done = set()
    if OUT.exists():
        cols = pd.read_csv(OUT, nrows=0).columns.tolist()
        if "primary_org" not in cols:
            sys.exit(f"{OUT} uses the old schema — run with --reverify first.")
        done = set(pd.read_csv(OUT, dtype=str)["id"])
    todo = [i for i in ids if i not in done]
    print(f"{len(ids)} safety papers with plaintext, {len(done)} done, "
          f"{len(todo)} to process ({len(SAFETY_ORGS)} orgs)")

    import csv
    import fcntl
    write_header = not OUT.exists()
    f = open(OUT, "a", newline="", encoding="utf-8")
    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
    w = csv.DictWriter(f, fieldnames=FIELDS)
    if write_header:
        w.writeheader()

    n = n_conf = n_llm = 0
    for rid in todo:
        conf, year = meta[rid]
        row, made = process_paper(rid, conf, year, llm, TEXT_DIR)
        w.writerow(row)
        f.flush()
        n += 1
        n_llm += made
        if row["confirmed"]:
            n_conf += 1
        if n % 50 == 0:
            print(f"  {n}/{len(todo)}  (LLM calls: {n_llm}, confirmed: {n_conf})")
    f.close()
    print(f"\nDone. {n} papers ({n_llm} LLM calls), {n_conf} with a confirmed org.")
    print(f"Output: {OUT}")


if __name__ == "__main__":
    main()
