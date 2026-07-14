#!/usr/bin/env python3
"""
Regenerate the website's org data in js/data.js from the org analysis, so the
site never has to be hand-edited after a verify_orgs.py re-run.

Rebuilds four arrays from data/org_verified.csv + data/org_plots/{orgs,funders}.csv:
  ORGS_ASSOC   — research orgs by ANY confirmed affiliation (one paper -> many orgs)
  ORGS_PRIMARY — each paper once, under its primary affiliation (Independent first)
  FUNDERS_LIST — funders by funding-acknowledgment count
  ORG_BY_YEAR  — per year, [year, org-or-funder, checked]: papers whose PRIMARY is a
                 named research org OR that acknowledge a funder (excludes papers
                 that are independent apart from a lone company author)
and refreshes the Who-Publishes summary numbers (research-org count, top org,
"N have no tracked org"). Curated legal-type labels in js/data.js are preserved.

Run after regenerating the plots:  python src/org_analysis/gen_web_data.py
"""

import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT))
from org_structure import org_type, PROGRAMS  # noqa: E402

DATAJS = ROOT / "js" / "data.js"
PLOTS = ROOT / "data" / "org_plots"
INDEP = "University/Independent/other"
TYPE_LABEL = {"corporate": "corporate", "PBC": "public-benefit corporation",
              "nonprofit": "nonprofit", "academic": "academic centre",
              "government": "government", "funder": "funder"}


def curated_labels(js):
    """Preserve any hand-tuned legal-type label already in js/data.js
    (e.g. OpenAI 'corporate -> PBC (2026)', MATS 'nonprofit fellowship')."""
    lab = {}
    for m in re.finditer(r"\['([^']+)',\s*\d+,\s*'([^']+)'\]", js):
        lab.setdefault(m.group(1), m.group(2))
    return lab


def label(name, curated):
    if name in curated and curated[name] != "funder":
        return curated[name]
    if name in PROGRAMS:
        return "nonprofit fellowship"
    return TYPE_LABEL[org_type(name, 2026)]


def js_rows(rows):
    return "[\n" + "\n".join(f"  ['{n}', {c}, '{t}']," for n, c, t in rows) + "\n]"


def splice(js, name, literal):
    new = f"const {name} = {literal};"
    js, k = re.subn(rf"const {name} = \[.*?\];", lambda _: new, js, count=1, flags=re.DOTALL)
    if not k:
        sys.exit(f"could not find `const {name} = [...]` in {DATAJS}")
    return js


def main():
    js = DATAJS.read_text()
    curated = curated_labels(js)

    o = pd.read_csv(PLOTS / "orgs.csv")
    o = o[o["organization"] != "University / Independent / not in list"].copy()
    o["primary"] = o["primary_papers"].astype(int)
    o["assoc"] = o["association_papers"].astype(int)

    v = pd.read_csv(ROOT / "data" / "org_verified.csv", dtype=str).fillna("")
    v["year"] = v["year"].astype(int)
    indep = int((v["primary_org"] == INDEP).sum())

    # ORGS_ASSOC (by association) and ORGS_PRIMARY (by primary, Independent first)
    a = o[o["assoc"] > 0].sort_values(["assoc", "organization"], ascending=[False, True])
    assoc = [(r["organization"], r["assoc"], label(r["organization"], curated))
             for _, r in a.iterrows()]
    p = o[o["primary"] > 0].sort_values(["primary", "organization"], ascending=[False, True])
    primary = [("Independent / University", indep, "no tracked org")] + \
              [(r["organization"], r["primary"], label(r["organization"], curated))
               for _, r in p.iterrows()]

    f = pd.read_csv(PLOTS / "funders.csv")
    funders = [(r["funder"], int(r["papers"]), "funder") for _, r in f.iterrows()]

    # ORG_BY_YEAR: primary is a named research org OR the paper has a funder
    counted = ((v["primary_org"] != "") & (v["primary_org"] != INDEP)) | (v["primary_funder"] != "")
    by_year = [(str(y), int(counted[v["year"] == y].sum()), int((v["year"] == y).sum()))
               for y in sorted(v["year"].unique())]
    by_year_lit = "[\n  " + ", ".join(f"['{y}', {c}, {t}]" for y, c, t in by_year) + ",\n]"

    js = splice(js, "ORGS_ASSOC", js_rows(assoc))
    js = splice(js, "ORGS_PRIMARY", js_rows(primary))
    js = splice(js, "FUNDERS_LIST", js_rows(funders))
    js = splice(js, "ORG_BY_YEAR", by_year_lit)

    # refresh the Who-Publishes summary numbers
    top = assoc[0]
    js = re.sub(r"(big: \{ num: )\d+( \}, bigUnit: 'orgs')", rf"\g<1>{len(assoc)}\2", js)
    js = re.sub(r"(k: 'Research orgs', v: ')\d+(')", rf"\g<1>{len(assoc)}\2", js)
    js = re.sub(r"(k: 'Top org', v: '[^·']+· )\d+(')", rf"\g<1>{top[1]}\2", js)
    js = re.sub(r"(scanned; )\d+( have no tracked org)", rf"\g<1>{indep}\2", js)

    DATAJS.write_text(js)
    print(f"Wrote {DATAJS}")
    print(f"  ORGS_ASSOC {len(assoc)} · ORGS_PRIMARY {len(primary)-1}+Independent · "
          f"FUNDERS {len(funders)} · ORG_BY_YEAR {len(by_year)} years")
    print(f"  top org (assoc): {top[0]} · {top[1]}   |   Independent (primary): {indep}")
    print(f"  ORG_BY_YEAR (org-or-funder / checked): "
          + ", ".join(f"{y}:{c}/{t}" for y, c, t in by_year))


if __name__ == "__main__":
    main()
