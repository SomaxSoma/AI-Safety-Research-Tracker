#!/usr/bin/env python3
"""
Regenerate the DETAILED CLASSES data in js/data.js from the classifier output
(data/{conf}/{year}/results.csv + papers.csv):

  SUBDOMAINS          — all-years, all-venue aggregate: every safety paper across
                        ICLR/ICML/NeurIPS 2019-2026 by subdomain.
  NOTABLE_SUBDOMAINS  — one example paper per subdomain, ranked by score first,
                        then recency (so a 7/7 paper wins, most recent among ties),
                        ordered by subdomain prominence.

Also refreshes the subdomains view's data-derived labels. The per-year SD_RAW
drilldown is left as-is (its sum equals SUBDOMAINS).

Run:  python src/gen_web_subdomains.py
"""

import glob
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATAJS = ROOT / "js" / "data.js"


def js_str(s):
    return str(s).replace("\\", "\\\\").replace("'", "\\'")


def load_safety():
    rows = []
    for rf in glob.glob(str(ROOT / "data" / "*" / "*" / "results.csv")):
        yd = Path(rf).parent
        res = pd.read_csv(rf, dtype=str)
        res = res[res["is_safety"].astype(str).str.lower().isin(["true", "1"])]
        pap = pd.read_csv(yd / "papers.csv", dtype=str)
        url = dict(zip(pap["id"], pap.get("url", pd.Series(dtype=str)).fillna("")))
        year = int(yd.name)
        for _, r in res.iterrows():
            sd = r.get("subdomain")
            if not (isinstance(sd, str) and sd):
                continue
            rows.append({"id": r["id"], "title": r["title"], "subdomain": sd,
                         "score": int(r["total_score"]) if str(r.get("total_score") or "").isdigit() else 0,
                         "year": year, "url": url.get(r["id"], "")})
    return pd.DataFrame(rows)


def main():
    df = load_safety()
    counts = df["subdomain"].value_counts()
    order = list(counts.index)  # by prominence
    total = int(counts.sum())
    n_sd = len(order)
    top3 = int(counts.iloc[:3].sum())
    rare_name, rare_n = counts.index[-1], int(counts.iloc[-1])

    # SUBDOMAINS aggregate (3 per line)
    items = [(n, int(counts[n])) for n in order]
    sd_lines = ["  " + ", ".join(f"['{js_str(n)}', {v}]" for n, v in items[i:i + 3]) + ","
                for i in range(0, len(items), 3)]
    sd_arr = "const SUBDOMAINS = [\n" + "\n".join(sd_lines) + "\n];"

    # NOTABLE_SUBDOMAINS: per subdomain, best score then most recent (id as stable tiebreak)
    notable = []
    for sd in order:
        best = df[df["subdomain"] == sd].sort_values(
            ["score", "year", "id"], ascending=[False, False, False]).iloc[0]
        notable.append((best["title"], sd, best["url"]))
    nt_lines = [f"  {{ t: '{js_str(t)}', d: '{js_str(d)}', u: '{js_str(u)}' }},"
                for t, d, u in notable]
    nt_arr = "const NOTABLE_SUBDOMAINS = [\n" + "\n".join(nt_lines) + "\n];"

    js = DATAJS.read_text()
    for name, arr in [("SUBDOMAINS", sd_arr), ("NOTABLE_SUBDOMAINS", nt_arr)]:
        js, k = re.subn(rf"const {name} = \[.*?\];", lambda _: arr, js, count=1, flags=re.DOTALL)
        if not k:
            sys.exit(f"could not find const {name}")

    # data-derived labels in the subdomains view (idempotent)
    js = re.sub(r"(chartUnit: ')[^']*(', *\n *kicker: 'DETAILED CLASSES')",
                rf"\g<1>all venues · 2019–2026 · {n_sd} of 17 · n={total:,}\2", js)
    js = re.sub(r"(kicker: 'DETAILED CLASSES', big: \{ num: )\d+", rf"\g<1>{items[0][1]}", js)
    js = re.sub(r"(k: 'Distinct subdomains', v: ')\d+( / 17')", rf"\g<1>{n_sd}\2", js)
    js = re.sub(r"(k: 'Top-3 share', v: ')\d+(%')", rf"\g<1>{round(top3 / total * 100)}\2", js)
    js = re.sub(r"\{ k: 'Rarest[^}]*\}", f"{{ k: 'Rarest', v: '{js_str(rare_name)} ({rare_n})' }}", js)
    js = re.sub(r"(countLabel: ')\d+ subdomains'", rf"\g<1>{n_sd} subdomains'", js)

    DATAJS.write_text(js)
    print(f"SUBDOMAINS: {n_sd}/17, n={total:,} · top {items[0][0]} ({items[0][1]})")
    print(f"NOTABLE_SUBDOMAINS: {len(notable)} papers (best score, then recent):")
    for t, d, u in notable:
        s = df[(df['subdomain'] == d) & (df['title'] == t)].iloc[0]
        print(f"  {d:28} {s['score']}/7 {s['year']}  {str(t)[:50]}")


if __name__ == "__main__":
    main()
