#!/usr/bin/env python3
"""
Cross-conference aggregate plots of the full classifier output
(reads every data/{conf}/{year}/results.csv):

  1. safety_share_by_year.png   — % of papers marked safety per year,
                                    pooled across ICLR + ICML + NeurIPS
  2. safety_share_by_conf.png   — same %, but three columns per year
                                    (ICLR / ICML / NeurIPS side by side)
  3. safety_areas_composition.png — line plot of each fine safety subdomain
                                    as a share of that year's safety papers
                                    (lines sum to 100% within each year)

Written to data/aggregate_plots/.
"""

import glob
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "aggregate_plots"

CONFS = ["iclr", "icml", "neurips"]
CONF_LABEL = {"iclr": "ICLR", "icml": "ICML", "neurips": "NeurIPS"}
CONF_COLOR = {"iclr": "#2a78d6", "icml": "#eb6834", "neurips": "#1baf7a"}

INK, INK2, GRID = "#0b0b0b", "#52514e", "#e6e6e3"


def load() -> pd.DataFrame:
    rows = []
    for f in sorted(glob.glob(str(ROOT / "data" / "*" / "*" / "results.csv"))):
        parts = Path(f).parts
        conf, year = parts[-3], int(parts[-2])
        d = pd.read_csv(f, dtype=str)
        d["conf"] = conf
        d["year"] = year
        d["is_safety"] = d["is_safety"].astype(str).str.lower().isin(["true", "1"])
        rows.append(d[["conf", "year", "is_safety", "subdomain"]])
    return pd.concat(rows, ignore_index=True)


def style(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.set_axisbelow(True)


def plot_by_year(df):
    g = df.groupby("year")["is_safety"].agg(["sum", "count"])
    years = list(g.index)
    pct = (g["sum"] / g["count"] * 100).tolist()

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(range(len(years)), pct, color="#2a78d6", width=0.66)
    for i, (p, n) in enumerate(zip(pct, g["count"])):
        ax.text(i, p + max(pct) * 0.012, f"{p:.1f}%", ha="center", va="bottom",
                fontsize=10, fontweight="bold", color=INK)
        ax.text(i, -max(pct) * 0.045, f"n={n:,}", ha="center", va="top",
                fontsize=8, color=INK2)
    ax.set_xticks(range(len(years)))
    ax.set_xticklabels(years)
    ax.set_ylabel("Papers marked AI-safety (%)", fontsize=11, color=INK2)
    ax.set_title("AI-safety share of accepted papers, by year",
                 fontsize=15, fontweight="bold", color=INK, pad=28)
    ax.text(0.0, 1.005, "Pooled across ICLR, ICML and NeurIPS. 2026 = ICLR + ICML only "
            "(NeurIPS 2026 not yet held).", transform=ax.transAxes,
            fontsize=8.5, color=INK2, va="bottom")
    ax.set_ylim(0, max(pct) * 1.16)
    style(ax)
    fig.tight_layout()
    fig.savefig(OUT / "safety_share_by_year.png", dpi=150, bbox_inches="tight",
                facecolor="white")
    plt.close(fig)
    print(f"Saved: {OUT/'safety_share_by_year.png'}")


def plot_by_conf(df):
    g = (df.groupby(["conf", "year"])["is_safety"].agg(["sum", "count"])
         .reset_index())
    g["pct"] = g["sum"] / g["count"] * 100
    years = sorted(df["year"].unique())
    w = 0.26

    fig, ax = plt.subplots(figsize=(11.5, 6))
    for j, conf in enumerate(CONFS):
        vals, present = [], []
        for k, y in enumerate(years):
            row = g[(g["conf"] == conf) & (g["year"] == y)]
            if len(row):
                vals.append(float(row["pct"].iloc[0]))
                present.append(k)
        xs = [k + (j - 1) * w for k in present]
        ax.bar(xs, vals, width=w, color=CONF_COLOR[conf], label=CONF_LABEL[conf])
        for x, v in zip(xs, vals):
            ax.text(x, v + 0.12, f"{v:.1f}", ha="center", va="bottom",
                    fontsize=7.5, color=INK2)
    ax.set_xticks(range(len(years)))
    ax.set_xticklabels(years)
    ax.set_ylabel("Papers marked AI-safety (%)", fontsize=11, color=INK2)
    ax.set_title("AI-safety share by conference, by year",
                 fontsize=15, fontweight="bold", color=INK, pad=10)
    ax.text(0.0, 1.005, "NeurIPS 2026 not yet held.", transform=ax.transAxes,
            fontsize=8.5, color=INK2, va="bottom")
    style(ax)
    ax.legend(loc="upper left", fontsize=10, frameon=False)
    fig.tight_layout()
    fig.savefig(OUT / "safety_share_by_conf.png", dpi=150, bbox_inches="tight",
                facecolor="white")
    plt.close(fig)
    print(f"Saved: {OUT/'safety_share_by_conf.png'}")


def plot_areas_composition(df):
    s = df[df["is_safety"]].copy()
    s["subdomain"] = s["subdomain"].fillna("(unspecified)")
    years = sorted(s["year"].unique())
    order = s["subdomain"].value_counts().index.tolist()  # most common first

    # share of that year's safety papers, per subdomain
    ct = (s.groupby(["year", "subdomain"]).size()
          .unstack(fill_value=0).reindex(columns=order, fill_value=0))
    share = ct.div(ct.sum(axis=1), axis=0) * 100

    import matplotlib.cm as cm
    colors = [cm.tab20(i % 20) for i in range(len(order))]

    fig, ax = plt.subplots(figsize=(12, 7))
    for name, col in zip(order, colors):
        ax.plot(years, share[name], marker="o", ms=4, lw=1.8, color=col, label=name)
    ax.set_xticks(years)
    ax.set_xticklabels(years)
    ax.set_ylabel("Share of that year's safety papers (%)", fontsize=11, color=INK2)
    ax.set_title("Composition of AI-safety research by subdomain, over time",
                 fontsize=15, fontweight="bold", color=INK, pad=28)
    ns = s.groupby("year").size()
    ax.text(0.0, 1.005, "Fine classification; lines sum to 100% within each year. "
            "Pooled across all three venues.  " +
            "  ".join(f"{y}: n={ns[y]}" for y in years),
            transform=ax.transAxes, fontsize=7.5, color=INK2, va="bottom")
    style(ax)
    ax.set_ylim(bottom=0)
    ax.legend(loc="center left", bbox_to_anchor=(1.005, 0.5), fontsize=8.5,
              frameon=False, title="Subdomain", title_fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / "safety_areas_composition.png", dpi=150, bbox_inches="tight",
                facecolor="white")
    plt.close(fig)
    print(f"Saved: {OUT/'safety_areas_composition.png'}")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    df = load()
    print(f"Loaded {len(df):,} classified papers "
          f"({df['is_safety'].sum():,} safety)")
    plot_by_year(df)
    plot_by_conf(df)
    plot_areas_composition(df)


if __name__ == "__main__":
    main()
