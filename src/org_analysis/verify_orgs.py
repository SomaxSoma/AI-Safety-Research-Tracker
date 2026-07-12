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
from org_structure import SAFETY_ORGS  # noqa: E402

OUT = ROOT / "data" / "org_verified.csv"
MODEL = "deepseek/deepseek-v4-flash"
CTX = 200          # chars each side of a keyword match
MAX_SNIPPETS = 3   # per org
ACK_RE = re.compile(r"acknowledg", re.IGNORECASE)

PROMPT = """You are checking whether a research paper is genuinely ASSOCIATED with organizations, versus merely mentioning or citing them.

The snippets below are from a paper's first page (title/authors/affiliations/abstract/intro) and its acknowledgments. For each listed organization, classify its relationship to THIS paper:
- "affiliation": an author's institution or employer
- "acknowledgment": a funder, grant, program, or party thanked (compute, mentorship, feedback)
- "mention": only cited, compared against, or used as a tool/platform/dataset host (e.g. "available on Hugging Face", "models like GPT-4")
- "absent": not really about this organization

Also pick the single PRIMARY organization behind the paper: the org that most of the authors are affiliated with (weigh author counts — e.g. 4 Anthropic authors vs 2 from a MATS program → Anthropic). Consider only orgs you marked "affiliation". If none are affiliations, fall back to the most prominent "acknowledgment" org; if none, use null.

Return ONLY a JSON object:
{"verdicts": {"<org>": "affiliation|acknowledgment|mention|absent", ...}, "primary": "<org name or null>"}"""


def snippets_for(region_text, org):
    out = []
    for alias in ORGS[org]["aliases"]:
        for m in _pattern(alias).finditer(region_text):
            s = region_text[max(0, m.start() - CTX): m.start() + len(alias) + CTX]
            out.append(" ".join(s.split()))
            if len(out) >= MAX_SNIPPETS:
                return out
    return out


def verify_paper(client, region_text, orgs):
    blocks = []
    for org in orgs:
        snips = snippets_for(region_text, org)
        if snips:
            blocks.append(f'"{org}":\n' + "\n".join(f"  - …{s}…" for s in snips))
    if not blocks:
        return {}, None
    user = PROMPT + "\n\nSnippets:\n" + "\n".join(blocks)
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
            verdicts = data.get("verdicts", {})
            primary = data.get("primary")
            if isinstance(primary, str) and primary.lower() in ("null", "none", ""):
                primary = None
            return verdicts, primary
        except Exception:
            continue
    return {}, None


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


def main():
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        sys.exit("Set OPENROUTER_API_KEY")
    llm = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=key)
    TEXT_DIR = ROOT / "data" / "plaintext"
    if not TEXT_DIR.exists():
        sys.exit(f"No plaintext found at {TEXT_DIR}. Run fetch_plaintext.py first.")

    meta = safety_paper_years()
    # every safety paper that has saved plaintext (self-contained, reproducible)
    ids = sorted(p.stem for p in TEXT_DIR.glob("*.txt") if p.stem in meta)

    done = set()
    if OUT.exists():
        done = set(pd.read_csv(OUT, dtype=str)["id"])
    todo = [i for i in ids if i not in done]
    print(f"{len(ids)} safety papers with plaintext, {len(done)} done, {len(todo)} to process "
          f"({len(SAFETY_ORGS)} orgs in the single safety class)")

    import csv
    import fcntl
    write_header = not OUT.exists()
    f = open(OUT, "a", newline="", encoding="utf-8")
    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
    w = csv.DictWriter(f, fieldnames=["id", "conference", "year", "candidates",
                                      "confirmed", "primary", "verdicts"])
    if write_header:
        w.writeheader()

    n = n_conf = n_llm = 0
    for rid in todo:
        conf, year = meta[rid]
        full = (TEXT_DIR / f"{rid}.txt").read_text(encoding="utf-8", errors="replace")
        region = full[:2500]
        am = ACK_RE.search(full)
        if am:
            region += "\n" + full[am.start():am.start() + 1500]

        cands = candidates_in(region)
        confirmed, verdicts, primary = [], {}, None
        if cands:  # only papers with a candidate cost an LLM call
            verdicts, primary = verify_paper(llm, region, cands)
            confirmed = [o for o in cands
                         if verdicts.get(o) in ("affiliation", "acknowledgment")]
            if primary not in confirmed:
                primary = confirmed[0] if confirmed else None
            n_llm += 1
        w.writerow({"id": rid, "conference": conf, "year": year,
                    "candidates": "; ".join(cands), "confirmed": "; ".join(confirmed),
                    "primary": primary or "", "verdicts": json.dumps(verdicts)})
        f.flush()
        n += 1
        if confirmed:
            n_conf += 1
        if n % 50 == 0:
            print(f"  {n}/{len(todo)}  (LLM calls: {n_llm}, confirmed-org papers: {n_conf})")
    f.close()
    print(f"\nDone. {n} papers ({n_llm} needed an LLM call), "
          f"{n_conf} with a confirmed safety-org association.")
    print(f"Output: {OUT}")


if __name__ == "__main__":
    main()
