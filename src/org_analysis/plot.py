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
from org_structure import TYPES, COLOR, LABEL, org_type, paper_bucket  # noqa: E402

INK, INK2, GRID = "#0b0b0b", "#52514e", "#e6e6e3"


def load() -> pd.DataFrame:
    # self-contained: org_verified has a row per safety paper with plaintext
    v = pd.read_csv(ROOT / "data" / "org_verified.csv", dtype=str)
    base = v[["id", "conference", "year"]].copy()
    base["orgs"] = [[o for o in str(c).split("; ") if o] if pd.notna(c) else []
                    for c in v["confirmed"]]
    base["primary"] = v["primary"].fillna("")
    base["year"] = base["year"].astype(int)
    base["bucket"] = [paper_bucket(o, y, p) for o, y, p in
                      zip(base["orgs"], base["year"], base["primary"])]
    print(f"LLM-verified associations ({len(base)} papers)")
    return base


def main():
    argparse.ArgumentParser().parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    df = load()

    years = sorted(df["year"].unique())
    ns, any_pct = [], []
    seg = {t: [] for t in TYPES}
    for y in years:
        s = df[df["year"] == y]
        n = len(s); ns.append(n)
        any_pct.append((s["bucket"].notna()).mean() * 100)
        for t in TYPES:
            seg[t].append((s["bucket"] == t).mean() * 100)

    # ---------- (A) combined ----------
    fig, ax = plt.subplots(figsize=(11, 6))
    ax.bar(range(len(years)), any_pct, color="#2a78d6", width=0.68)
    for i, (v, n) in enumerate(zip(any_pct, ns)):
        ax.text(i, v + 0.6, f"{v:.0f}%", ha="center", va="bottom", fontsize=10, fontweight="bold", color=INK)
        ax.text(i, -2.6, f"n={n}", ha="center", va="top", fontsize=8, color=INK2)
    ax.set_xticks(range(len(years))); ax.set_xticklabels(years)
    ax.set_ylabel("Safety papers with a safety-org association (%)", fontsize=11, color=INK2)
    ax.set_title("Share of AI-safety papers backed by a tracked safety org, by year",
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
    for t in TYPES:
        ax.bar(x, seg[t], bottom=bottom, color=COLOR[t], width=0.68, label=LABEL[t])
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

    plot_top_orgs(df)


def plot_top_orgs(df, topn=20):
    from collections import Counter
    c = Counter()
    for orgs in df["orgs"]:
        for o in orgs:
            c[o] += 1
    data = c.most_common(topn)
    names = [n for n, _ in data][::-1]
    vals = [v for _, v in data][::-1]
    # colour each bar by its structural type (use latest year for OpenAI)
    cols = [COLOR[org_type(n, 2026)] for n in names]

    fig, ax = plt.subplots(figsize=(9, 8))
    ax.barh(names, vals, color=cols, edgecolor="white", linewidth=0.6)
    for i, v in enumerate(vals):
        ax.text(v + max(vals) * 0.01, i, str(v), va="center", fontsize=9, fontweight="bold", color=INK)
    ax.set_xlabel("Safety papers (LLM-verified association)", fontsize=10, color=INK2)
    ax.set_title("Top orgs behind AI-safety papers (verified)", fontsize=14,
                 fontweight="bold", color=INK, pad=10)
    ax.set_xlim(0, max(vals) * 1.12)
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)
    # legend for the type colours
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=COLOR[t], label=LABEL[t].split(" (")[0]) for t in TYPES],
              loc="lower right", fontsize=9, frameon=False)
    fig.tight_layout()
    fig.savefig(OUT / "top_orgs_verified.png", dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig); print(f"Saved: {OUT/'top_orgs_verified.png'}")


if __name__ == "__main__":
    main()
