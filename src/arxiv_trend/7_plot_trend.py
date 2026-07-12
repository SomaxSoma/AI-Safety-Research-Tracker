#!/usr/bin/env python3
"""
Plot the monthly fraction of arXiv ML papers classified as AI-safety.

Reads:  data/arxiv/predictions.csv  (from classify_arxiv.py)
Writes: data/arxiv/monthly_trend.csv
        data/arxiv/plots/safety_trend.png

Design (per the dataviz method):
  - change-over-time -> line; single quantity -> single hue (validated blue)
  - a separate lower panel for monthly volume (NEVER a dual y-axis)
  - raw monthly points + a 3-month rolling mean; a binomial ±1 SE band
  - recessive grid, thin marks, direct label on the final value
"""

from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
ARXIV = ROOT / "data" / "arxiv"
PLOTS = ARXIV / "plots"

BLUE = "#2a78d6"      # validated categorical slot 1
INK = "#0b0b0b"
INK2 = "#52514e"
GRID = "#e6e6e3"
BAR = "#c9c8c3"


def main():
    PLOTS.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(ARXIV / "predictions.csv", dtype={"ym": str})
    df = df[df["ym"].notna()].copy()

    g = df.groupby("ym").agg(n=("is_safety_pred", "size"),
                             n_safety=("is_safety_pred", "sum")).reset_index()
    g["frac"] = g["n_safety"] / g["n"]
    g["date"] = pd.to_datetime(g["ym"] + "-01")
    g = g.sort_values("date").reset_index(drop=True)
    # Restrict to fully-observed range (drop any stray future/short months)
    g = g[g["n"] >= 50].reset_index(drop=True)

    g["roll"] = g["frac"].rolling(3, center=True, min_periods=1).mean()
    g["se"] = np.sqrt(g["frac"] * (1 - g["frac"]) / g["n"])

    g.to_csv(ARXIV / "monthly_trend.csv", index=False)

    fig, (ax, axv) = plt.subplots(
        2, 1, figsize=(13, 7.5), sharex=True,
        gridspec_kw={"height_ratios": [3.2, 1], "hspace": 0.08})

    # --- Top: % safety per month ---
    ax.fill_between(g["date"], (g["roll"] - g["se"]) * 100, (g["roll"] + g["se"]) * 100,
                    color=BLUE, alpha=0.15, linewidth=0)
    ax.scatter(g["date"], g["frac"] * 100, s=14, color=BLUE, alpha=0.35,
               label="Monthly", zorder=3)
    ax.plot(g["date"], g["roll"] * 100, color=BLUE, lw=2.2,
            label="3-month rolling mean", zorder=4)

    # Direct label on final rolling value
    last = g.iloc[-1]
    ax.annotate(f"{last['roll']*100:.1f}%",
                xy=(last["date"], last["roll"] * 100),
                xytext=(8, 0), textcoords="offset points",
                va="center", ha="left", fontsize=11, fontweight="bold", color=INK)

    ax.set_ylabel("Papers classified as AI safety (%)", fontsize=11, color=INK2)
    ax.set_title("AI-safety share of arXiv ML papers, 2019–2026",
                 fontsize=15, fontweight="bold", color=INK, pad=12)
    ax.set_ylim(0, max(g["frac"].max(), g["roll"].max()) * 100 * 1.12)
    ax.legend(loc="upper left", fontsize=10, frameon=False)
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)

    # subtitle line: model + categories
    ax.text(0.0, 1.005,
            "cs.LG · cs.AI · cs.CL · stat.ML   |   TF-IDF+LogReg vs LLM labels: "
            "71% precision / 79% recall (PR-AUC 0.85), threshold calibrated on 3,000 arXiv papers",
            transform=ax.transAxes, fontsize=9, color=INK2, va="bottom")

    # --- Bottom: monthly volume (context, not a dual axis) ---
    axv.bar(g["date"], g["n"], width=22, color=BAR, linewidth=0)
    axv.set_ylabel("Papers / month", fontsize=10, color=INK2)
    axv.grid(axis="y", color=GRID, lw=0.8)
    axv.set_axisbelow(True)
    for s in ("top", "right"):
        axv.spines[s].set_visible(False)

    axv.xaxis.set_major_locator(mdates.YearLocator())
    axv.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    axv.set_xlabel("Submission month", fontsize=11, color=INK2)

    fig.savefig(PLOTS / "safety_trend.png", dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Saved: {PLOTS/'safety_trend.png'}")
    print(f"Saved: {ARXIV/'monthly_trend.csv'}")
    print(f"\nRange: {g['ym'].iloc[0]} .. {g['ym'].iloc[-1]}  ({len(g)} months)")
    print(f"Total papers: {g['n'].sum():,}")
    print(f"Safety share: {g['ym'].iloc[0]}={g['frac'].iloc[0]*100:.2f}%  ->  "
          f"{g['ym'].iloc[-1]}={g['frac'].iloc[-1]*100:.2f}%")


if __name__ == "__main__":
    main()
