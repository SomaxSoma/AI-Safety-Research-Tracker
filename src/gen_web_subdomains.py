#!/usr/bin/env python3
"""
Regenerate the DETAILED CLASSES default chart in js/data.js as the ALL-YEARS,
ALL-VENUE aggregate — every safety paper across ICLR/ICML/NeurIPS 2019-2026 by
subdomain — from data/{conf}/{year}/results.csv, and refresh the subdomains
view's data-derived labels (chartUnit, top count, distinct count, top-3 share,
rarest, countLabel). The per-year SD_RAW drilldown is left as-is; its sum equals
this aggregate.

Run:  python src/gen_web_subdomains.py
"""

import glob
import re
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATAJS = ROOT / "js" / "data.js"


def main():
    c = Counter()
    for f in glob.glob(str(ROOT / "data" / "*" / "*" / "results.csv")):
        d = pd.read_csv(f, dtype=str)
        s = d[d["is_safety"].astype(str).str.lower().isin(["true", "1"])]
        for sd in s["subdomain"].dropna():
            if sd:
                c[sd] += 1
    items = c.most_common()
    total = sum(c.values())
    n_sd = len(items)
    top3 = sum(v for _, v in items[:3])
    rare_name, rare_n = items[-1]

    # SUBDOMAINS array, 3 entries per line (matches the file's style)
    lines = ["  " + ", ".join(f"['{n}', {v}]" for n, v in items[i:i + 3]) + ","
             for i in range(0, len(items), 3)]
    arr = "const SUBDOMAINS = [\n" + "\n".join(lines) + "\n];"

    js = DATAJS.read_text()
    js, k = re.subn(r"const SUBDOMAINS = \[.*?\];", lambda _: arr, js, count=1, flags=re.DOTALL)
    if not k:
        sys.exit("could not find const SUBDOMAINS")

    # data-derived labels in the subdomains view (idempotent regexes)
    js = re.sub(r"(chartUnit: ')[^']*(', *\n *kicker: 'DETAILED CLASSES')",
                rf"\g<1>all venues · 2019–2026 · {n_sd} of 17 · n={total:,}\2", js)
    js = re.sub(r"(kicker: 'DETAILED CLASSES', big: \{ num: )\d+", rf"\g<1>{items[0][1]}", js)
    js = re.sub(r"(k: 'Distinct subdomains', v: ')\d+( / 17')", rf"\g<1>{n_sd}\2", js)
    js = re.sub(r"(k: 'Top-3 share', v: ')\d+(%')", rf"\g<1>{round(top3 / total * 100)}\2", js)
    js = re.sub(r"\{ k: 'Rarest[^}]*\}",
                f"{{ k: 'Rarest', v: '{rare_name} ({rare_n})' }}", js)
    js = re.sub(r"(countLabel: ')\d+ subdomains'", rf"\g<1>{n_sd} subdomains'", js)

    DATAJS.write_text(js)
    print(f"SUBDOMAINS aggregate: {n_sd}/17 subdomains, n={total:,}")
    print(f"  top: {items[0][0]} ({items[0][1]}) · top-3 share {round(top3 / total * 100)}%"
          f" · rarest {rare_name} ({rare_n})")
    print("  top 3:", ", ".join(f"{n} {v}" for n, v in items[:3]))


if __name__ == "__main__":
    main()
