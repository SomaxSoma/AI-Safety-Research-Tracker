#!/usr/bin/env python3
"""
Plot the org backing of safety papers, per year:
  (A) combined  — % of safety papers with ANY safety-org association
  (B) discerned — same total, split into corporate / PBC / nonprofit,
                  with the total % labelled on top

Org structure types (a single safety-org class, typed by legal structure):
  PBC        Anthropic; OpenAI from 2026 (after its late-2025 PBC conversion)
  corporate  Google DeepMind, OpenAI before 2026, safety startups
  nonprofit  everything else — independent nonprofits, academic centres,
             government safety institutes, funders

A paper with orgs of several types is assigned to one bucket by priority
PBC > corporate > nonprofit, so the three sum to the combined total.

Reads the LLM-VERIFIED associations (data/org_verified.csv, 'confirmed' column)
when present; otherwise falls back to raw keyword hits (data/org_matches.csv)
for a preview (pass --raw).
"""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "org_plots"

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))  # for org_structure
from org_structure import TYPES, COLOR, LABEL, org_type  # noqa: E402

INK, INK2, GRID = "#0b0b0b", "#52514e", "#e6e6e3"
INDEP_COLOR = "#9a9a95"  # funded, but no tracked research-org affiliation
INDEP_LABEL = "University / Independent / not in list"

# by-type buckets: research-org types + Independent (funders get their own plot)
BUCKET_TYPES = ["PBC", "corporate", "nonprofit", "academic", "government", "independent"]
RESEARCH_PRIORITY = ["PBC", "corporate", "academic", "government", "nonprofit"]


def type_bucket(orgs, year, primary=None):
    """A paper's home type: its research-org type, or 'independent' if the only
    confirmed orgs are funders. None if no confirmed org. Consistent with the
    research_orgs / funders split (funders are never a paper's home type)."""
    research = [o for o in orgs if org_type(o, year) != "funder"]
    if not research:
        return "independent" if orgs else None
    if primary and primary in research:
        return org_type(primary, year)
    types = {org_type(o, year) for o in research}
    return next((t for t in RESEARCH_PRIORITY if t in types), "nonprofit")


def bucket_color(t):
    return INDEP_COLOR if t == "independent" else COLOR[t]


def bucket_label(t):
    return INDEP_LABEL if t == "independent" else LABEL[t]


def load() -> pd.DataFrame:
    # self-contained: org_verified has a row per safety paper with plaintext
    v = pd.read_csv(ROOT / "data" / "org_verified.csv", dtype=str)
    base = v[["id", "conference", "year"]].copy()
    base["orgs"] = [[o for o in str(c).split("; ") if o] if pd.notna(c) else []
                    for c in v["confirmed"]]
    base["primary"] = v["primary"].fillna("")
    base["year"] = base["year"].astype(int)
    base["bucket"] = [type_bucket(o, y, p) for o, y, p in
                      zip(base["orgs"], base["year"], base["primary"])]
    print(f"LLM-verified associations ({len(base)} papers)")
    return base


def main():
    argparse.ArgumentParser().parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    df = load()

    years = sorted(df["year"].unique())
    ns, any_pct = [], []
    seg = {t: [] for t in BUCKET_TYPES}
    for y in years:
        s = df[df["year"] == y]
        n = len(s); ns.append(n)
        any_pct.append((s["bucket"].notna()).mean() * 100)
        for t in BUCKET_TYPES:
            seg[t].append((s["bucket"] == t).mean() * 100)

    # ---------- (A) combined ----------
    fig, ax = plt.subplots(figsize=(11, 6))
    ax.bar(range(len(years)), any_pct, color="#2a78d6", width=0.68)
    for i, (v, n) in enumerate(zip(any_pct, ns)):
        ax.text(i, v + 0.6, f"{v:.0f}%", ha="center", va="bottom", fontsize=10, fontweight="bold", color=INK)
        ax.text(i, -2.6, f"n={n}", ha="center", va="top", fontsize=8, color=INK2)
    ax.set_xticks(range(len(years))); ax.set_xticklabels(years)
    ax.set_ylabel("AI-safety papers backed by a safety org (%)", fontsize=11, color=INK2)
    ax.set_title("Share of AI-safety papers backed by a safety org, by year",
                 fontsize=14, fontweight="bold", color=INK, pad=10)
    ax.set_ylim(0, max(any_pct) * 1.18); ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "org_backed_combined.png", dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig); print(f"Saved: {OUT/'org_backed_combined.png'}")

    # ---------- (B) discerned ----------
    fig, ax = plt.subplots(figsize=(11.5, 6.8))
    x = range(len(years))
    bottom = [0.0] * len(years)
    for t in BUCKET_TYPES:
        ax.bar(x, seg[t], bottom=bottom, color=bucket_color(t), width=0.68,
               label=bucket_label(t))
        bottom = [b + s for b, s in zip(bottom, seg[t])]
    for i in x:
        tot = any_pct[i]
        ax.text(i, tot + 0.6, f"{tot:.0f}%", ha="center", va="bottom", fontsize=10, fontweight="bold", color=INK)
        ax.text(i, -2.6, f"n={ns[i]}", ha="center", va="top", fontsize=8, color=INK2)
    ax.set_xticks(list(x)); ax.set_xticklabels(years)
    ax.set_ylabel("Share of safety papers (%)", fontsize=11, color=INK2)
    ax.set_title("AI-safety papers by backing org type, by year",
                 fontsize=14, fontweight="bold", color=INK, pad=10)
    ax.set_ylim(0, max(any_pct) * 1.20); ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    ax.legend(loc="upper left", fontsize=8.5, frameon=False, ncol=2)
    fig.tight_layout()
    fig.savefig(OUT / "org_backed_by_type.png", dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig); print(f"Saved: {OUT/'org_backed_by_type.png'}")

    orgc, fundc, independent = split_orgs(df)
    plot_orgs(orgc, independent)
    plot_funders(fundc)
    write_org_csvs(orgc, fundc, independent)
    plot_prevalence_split()


def split_orgs(df):
    """Tally confirmed orgs, separating research orgs from funders. A paper whose
    only confirmed orgs are funders contributes to a synthetic 'Independent'
    bucket — funded, but not affiliated with any tracked research org."""
    from collections import Counter
    orgc, fundc = Counter(), Counter()
    independent = 0
    for orgs in df["orgs"]:
        research = [o for o in orgs if org_type(o, 2026) != "funder"]
        funders = [o for o in orgs if org_type(o, 2026) == "funder"]
        for o in research:
            orgc[o] += 1
        for o in funders:
            fundc[o] += 1
        if funders and not research:
            independent += 1
    return orgc, fundc, independent


def _barh(names, vals, cols, title, xlabel, fname, legend=None):
    fig, ax = plt.subplots(figsize=(9, max(4, len(names) * 0.30)))
    ax.barh(names, vals, color=cols, edgecolor="white", linewidth=0.6)
    for i, v in enumerate(vals):
        ax.text(v + max(vals) * 0.01, i, str(v), va="center", fontsize=8.5,
                fontweight="bold", color=INK)
    ax.set_xlabel(xlabel, fontsize=10, color=INK2)
    ax.set_title(title, fontsize=14, fontweight="bold", color=INK, pad=10)
    ax.set_xlim(0, max(vals) * 1.12)
    ax.tick_params(axis="y", labelsize=8.5)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="x", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    if legend:
        ax.legend(handles=legend, loc="lower right", fontsize=9, frameon=False)
    fig.tight_layout()
    fig.savefig(OUT / fname, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Saved: {OUT/fname}")


def plot_orgs(orgc, independent):
    """Research orgs behind safety papers; funder-only papers -> Independent."""
    from matplotlib.patches import Patch
    items = sorted(list(orgc.items()) + [(INDEP_LABEL, independent)],
                   key=lambda kv: kv[1])  # ascending for barh
    names = [n for n, _ in items]
    vals = [v for _, v in items]
    cols = [INDEP_COLOR if n == INDEP_LABEL else COLOR[org_type(n, 2026)]
            for n in names]
    legend = [Patch(color=COLOR[t], label=LABEL[t].split(" (")[0])
              for t in TYPES if t != "funder"]
    legend.append(Patch(color=INDEP_COLOR, label=INDEP_LABEL))
    _barh(names, vals, cols, "Research orgs behind AI-safety papers",
          "Number of safety papers", "research_orgs.png", legend)


def plot_funders(fundc):
    """Funders acknowledged by safety papers (funding credits, not affiliations)."""
    items = sorted(fundc.items(), key=lambda kv: kv[1])
    names = [n for n, _ in items]
    vals = [v for _, v in items]
    _barh(names, vals, [COLOR["funder"]] * len(names),
          "Funders behind AI-safety papers",
          "Safety papers acknowledging the funder", "funders.png")


def write_org_csvs(orgc, fundc, independent):
    """Persist the two tallies next to the plots."""
    import csv
    org_rows = [(n, org_type(n, 2026), c) for n, c in orgc.items()]
    org_rows.append((INDEP_LABEL, "independent", independent))
    org_rows.sort(key=lambda r: -r[2])
    with open(OUT / "orgs.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["organization", "type", "papers"])
        w.writerows(org_rows)
    fund_rows = sorted(fundc.items(), key=lambda r: -r[1])
    with open(OUT / "funders.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["funder", "papers"])
        w.writerows(fund_rows)
    print(f"Saved: {OUT/'orgs.csv'} ({len(org_rows)} rows), "
          f"{OUT/'funders.csv'} ({len(fund_rows)} rows)")


def yearly_totals():
    """Per year: (total papers, safety papers). Excludes ICML 2026 (no PDFs), to
    match org coverage."""
    tot, saf = {}, {}
    for conf in ["iclr", "icml", "neurips"]:
        cdir = ROOT / "data" / conf
        if not cdir.exists():
            continue
        for yd in sorted(cdir.iterdir()):
            if conf == "icml" and yd.name == "2026":
                continue
            r = yd / "results.csv"
            if not r.exists():
                continue
            d = pd.read_csv(r, dtype=str)
            y = int(yd.name)
            tot[y] = tot.get(y, 0) + len(d)
            saf[y] = saf.get(y, 0) + int(d["is_safety"].astype(str).str.lower()
                                         .isin(["true", "1"]).sum())
    return tot, saf


def plot_prevalence_split():
    """Safety share of ALL papers per year, split into org-affiliated (bottom)
    vs no detected affiliation (top)."""
    tot, saf = yearly_totals()
    v = pd.read_csv(ROOT / "data" / "org_verified.csv", dtype=str)
    v["year"] = v["year"].astype(int)
    v["has"] = v["confirmed"].fillna("").str.len() > 0
    affil = v[v["has"]].groupby("year").size().to_dict()

    years = sorted(tot)
    aff_pct = [affil.get(y, 0) / tot[y] * 100 for y in years]
    saf_pct = [saf[y] / tot[y] * 100 for y in years]
    unaff_pct = [s - a for s, a in zip(saf_pct, aff_pct)]

    fig, ax = plt.subplots(figsize=(11, 6.2))
    x = range(len(years))
    ax.bar(x, aff_pct, color="#2a78d6", width=0.68, label="Safety, org-affiliated")
    ax.bar(x, unaff_pct, bottom=aff_pct, color="#c9c8c3", width=0.68,
           label="Safety, no safety-org affiliation")
    for i in x:
        if aff_pct[i] > 0.4:
            ax.text(i, aff_pct[i] / 2, f"{aff_pct[i]:.1f}%", ha="center", va="center",
                    fontsize=8.5, fontweight="bold", color="white")
        ax.text(i, saf_pct[i] + saf_pct[i] * 0.02 + 0.05, f"{saf_pct[i]:.1f}%", ha="center",
                va="bottom", fontsize=9.5, fontweight="bold", color=INK)
    ax.set_xticks(list(x)); ax.set_xticklabels(years)
    ax.set_ylabel("Share of ALL papers that year (%)", fontsize=11, color=INK2)
    ax.set_title("AI-safety share of papers, split by org affiliation",
                 fontsize=14, fontweight="bold", color=INK, pad=30)
    ax.text(0.0, 1.015,
            "Each column is that year's AI-safety share of all papers; blue is the part affiliated "
            "with a safety org. ICML 2026 excluded (no PDFs).",
            transform=ax.transAxes, fontsize=8.5, color=INK2, va="bottom")
    ax.set_ylim(0, max(saf_pct) * 1.18)
    ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
    ax.legend(loc="upper left", fontsize=9, frameon=False)
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "safety_prevalence_split.png", dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig); print(f"Saved: {OUT/'safety_prevalence_split.png'}")


if __name__ == "__main__":
    main()
