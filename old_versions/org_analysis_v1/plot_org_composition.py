#!/usr/bin/env python3
"""
Plot, per year, the fraction of (parsed) safety papers affiliated with:
  - a safety-only org (independent safety orgs / funders / programs)
  - a safety-adjacent lab (Anthropic/OpenAI/DeepMind/... with a safety agenda)
  - no tracked org

Rule: a single safety-only hit overrides safety-adjacent (a paper with both
counts as safety-only).

Reads data/org_matches.csv (from org_detect.py). Only status=="ok" papers are
counted (ICML 2026 has no PDFs and is excluded).
"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "org_plots"

SO = "#2a78d6"    # safety-only  (blue)
SA = "#eda100"    # safety-adjacent (amber)
NO = "#c9c8c3"    # no org (gray)
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e6e6e3"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(ROOT / "data" / "org_matches.csv", dtype=str)
    ok = df[df["status"] == "ok"].copy()
    ok["year"] = ok["year"].astype(int)
    has_so = ok["safety_only"].fillna("").str.len() > 0
    has_sa = ok["safety_adjacent"].fillna("").str.len() > 0
    ok["cat"] = ["safety_only" if so else "safety_adjacent" if sa else "no_org"
                 for so, sa in zip(has_so, has_sa)]

    years = sorted(ok["year"].unique())
    frac = {c: [] for c in ["safety_only", "safety_adjacent", "no_org"]}
    ns = []
    for y in years:
        s = ok[ok["year"] == y]
        ns.append(len(s))
        for c in frac:
            frac[c].append((s["cat"] == c).mean() * 100)

    fig, ax = plt.subplots(figsize=(12, 6.5))
    x = range(len(years))
    b1 = frac["safety_only"]
    b2 = frac["safety_adjacent"]
    b3 = frac["no_org"]
    ax.bar(x, b1, color=SO, label="Safety-only org", width=0.72)
    ax.bar(x, b2, bottom=b1, color=SA, label="Safety-adjacent lab", width=0.72)
    ax.bar(x, b3, bottom=[i + j for i, j in zip(b1, b2)], color=NO,
           label="No tracked org", width=0.72)

    # n annotations above bars
    for i, n in enumerate(ns):
        ax.text(i, 101.5, f"n={n}", ha="center", va="bottom", fontsize=9,
                color=INK2, fontweight="bold" if n >= 50 else "normal")

    # % labels inside the safety segments when big enough
    for i in x:
        if b1[i] >= 6:
            ax.text(i, b1[i] / 2, f"{b1[i]:.0f}%", ha="center", va="center",
                    fontsize=9, color="white", fontweight="bold")
        if b2[i] >= 8:
            ax.text(i, b1[i] + b2[i] / 2, f"{b2[i]:.0f}%", ha="center", va="center",
                    fontsize=9, color="white", fontweight="bold")

    ax.set_xticks(list(x))
    ax.set_xticklabels(years)
    ax.set_ylim(0, 108)
    ax.set_ylabel("Share of parsed safety papers (%)", fontsize=11, color=INK2)
    ax.set_title("Organisational affiliation of AI-safety papers, by year",
                 fontsize=15, fontweight="bold", color=INK, pad=26)
    ax.text(0.0, 1.02,
            "Conference safety papers (DeepSeek-labelled); affiliations + acknowledgments. "
            "A safety-only hit overrides safety-adjacent.  ICML 2026 excluded (no PDFs).",
            transform=ax.transAxes, fontsize=9, color=INK2, va="bottom")
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.14), ncol=3,
              fontsize=10, frameon=False)
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)

    fig.tight_layout()
    fig.savefig(OUT / "org_composition_by_year.png", dpi=150,
                bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Saved: {OUT/'org_composition_by_year.png'}")

    plot_top_orgs(ok)


def plot_top_orgs(ok, topn=15):
    from collections import Counter

    def counts(col):
        c = Counter()
        for s in ok[col].fillna(""):
            for o in [x for x in s.split("; ") if x]:
                c[o] += 1
        return c

    so = counts("safety_only").most_common(topn)
    sa = counts("safety_adjacent").most_common(topn)

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(15, 6.5))
    for ax, data, color, title in [
        (a1, sa, SA, "Safety-adjacent labs"),
        (a2, so, SO, "Safety-only orgs"),
    ]:
        names = [n for n, _ in data][::-1]
        vals = [v for _, v in data][::-1]
        ax.barh(names, vals, color=color, edgecolor="white", linewidth=0.6)
        for i, v in enumerate(vals):
            ax.text(v + max(vals) * 0.01, i, str(v), va="center", fontsize=9,
                    fontweight="bold", color=INK)
        ax.set_title(title, fontsize=13, fontweight="bold", color=INK, pad=8)
        ax.set_xlabel("Safety papers", fontsize=10, color=INK2)
        ax.set_xlim(0, max(vals) * 1.12)
        ax.tick_params(axis="y", labelsize=10)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        ax.grid(axis="x", color=GRID, lw=0.8)
        ax.set_axisbelow(True)

    fig.suptitle("Top organisations behind AI-safety papers (parsed conference safety papers)",
                 fontsize=15, fontweight="bold", color=INK, y=1.0)
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    fig.savefig(OUT / "top_orgs.png", dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Saved: {OUT/'top_orgs.png'}")


if __name__ == "__main__":
    main()
