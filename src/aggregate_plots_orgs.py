#!/usr/bin/env python3
"""
Same cross-conference aggregate views as aggregate_plots.py, but restricted to
the safety papers with an LLM-VERIFIED safety-org affiliation
(data/org_verified.csv, 'confirmed' non-empty) — 325 papers.

Subdomain colours/order are inherited from the FULL safety set, so these panels
line up with the all-safety versions for side-by-side reading.

Coverage caveat: org affiliation was only detected where paper plaintext was
fetched (see data/plaintext/ via fetch_plaintext.py; ICML 2026 has no PDFs).
The exact covered conference-years are computed from the data at plot time and
printed in each share plot's caption, so the two share-of-total plots only show
covered conference-years and every count is a LOWER BOUND on real affiliation.

Written to data/aggregate_plots/org_only/.
"""

import glob
from pathlib import Path

import matplotlib.cm as cm
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "aggregate_plots" / "org_only"

CONFS = ["iclr", "icml", "neurips"]
CONF_LABEL = {"iclr": "ICLR", "icml": "ICML", "neurips": "NeurIPS"}
CONF_COLOR = {"iclr": "#2a78d6", "icml": "#eb6834", "neurips": "#1baf7a"}
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e6e6e3"


def _compact_years(years):
    """[2024,2025,2026] -> '2024-26'; [2020,2023,2024,2025] -> '2020, 2023-25'."""
    ys = sorted(set(int(y) for y in years))
    if not ys:
        return ""
    runs, start, prev = [], ys[0], ys[0]
    for y in ys[1:] + [None]:
        if y == prev + 1:
            prev = y
            continue
        runs.append((start, prev))
        start = prev = y
    return ", ".join(str(a) if a == b else f"{a}-{str(b)[-2:]}" for a, b in runs)


def covered_str(covered):
    """Human-readable covered conf-years, computed from the data (not hardcoded),
    so the caption stays correct as coverage changes."""
    by = {}
    for conf, year in covered:
        by.setdefault(conf, []).append(year)
    parts = [f"{CONF_LABEL[c]} {_compact_years(by[c])}" for c in CONFS if c in by]
    return "; ".join(parts)


def load_results() -> pd.DataFrame:
    rows = []
    for f in sorted(glob.glob(str(ROOT / "data" / "*" / "*" / "results.csv"))):
        parts = Path(f).parts
        conf, year = parts[-3], int(parts[-2])
        d = pd.read_csv(f, dtype=str)
        d["conf"] = conf
        d["year"] = year
        d["is_safety"] = d["is_safety"].astype(str).str.lower().isin(["true", "1"])
        rows.append(d[["id", "conf", "year", "is_safety", "subdomain"]])
    return pd.concat(rows, ignore_index=True)


def subdomain_palette(res):
    """Global order + stable colour, from the full safety set (matches the
    all-safety plots)."""
    s = res[res["is_safety"]].copy()
    s["subdomain"] = s["subdomain"].fillna("(unspecified)")
    order = s["subdomain"].value_counts().index.tolist()
    colors = {name: cm.tab20(i % 20) for i, name in enumerate(order)}
    return order, colors


def style(ax):
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.set_axisbelow(True)


def org_frame(res):
    """Org-affiliated safety papers with their subdomain + covered-cell totals."""
    v = pd.read_csv(ROOT / "data" / "org_verified.csv", dtype=str)
    v["year"] = v["year"].astype(int)
    v["has"] = v["confirmed"].fillna("").str.len() > 0
    covered = set(map(tuple, v[["conference", "year"]].drop_duplicates().values))
    org = v[v["has"]][["id", "conference", "year"]].rename(
        columns={"conference": "conf"})
    org = org.merge(res[["id", "subdomain"]], on="id", how="left")
    org["subdomain"] = org["subdomain"].fillna("(unspecified)")
    # totals per covered conf-year (denominator for share plots)
    tot = (res[res.apply(lambda r: (r["conf"], r["year"]) in covered, axis=1)]
           .groupby(["conf", "year"]).size().rename("total").reset_index())
    return org, tot, covered


def plot_share_by_year(org, tot, cov):
    aff = org.groupby("year").size().rename("aff")
    tt = tot.groupby("year")["total"].sum()
    years = sorted(tt.index)
    pct = [aff.get(y, 0) / tt[y] * 100 for y in years]

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(range(len(years)), pct, color="#2a78d6", width=0.66)
    for i, y in enumerate(years):
        ax.text(i, pct[i] + max(pct) * 0.02, f"{pct[i]:.2f}%", ha="center",
                va="bottom", fontsize=9.5, fontweight="bold", color=INK)
        ax.text(i, -max(pct) * 0.05, f"n={aff.get(y,0)}", ha="center", va="top",
                fontsize=8, color=INK2)
    ax.set_xticks(range(len(years)))
    ax.set_xticklabels(years)
    ax.set_ylabel("Org-affiliated safety papers,\n% of all accepted papers",
                  fontsize=11, color=INK2)
    ax.set_title("Org-affiliated AI-safety share of papers, by year",
                 fontsize=15, fontweight="bold", color=INK, pad=28)
    ax.text(0.0, 1.005, "Share of all accepted papers affiliated with a safety org. "
            f"Conference-years shown: {cov}.",
            transform=ax.transAxes, fontsize=8, color=INK2, va="bottom")
    ax.set_ylim(0, max(pct) * 1.16)
    style(ax)
    fig.tight_layout()
    fig.savefig(OUT / "org_share_by_year.png", dpi=150, bbox_inches="tight",
                facecolor="white")
    plt.close(fig)
    print(f"Saved: {OUT/'org_share_by_year.png'}")


def plot_share_by_conf(org, tot, cov):
    aff = org.groupby(["conf", "year"]).size().rename("aff").reset_index()
    g = tot.merge(aff, on=["conf", "year"], how="left")
    g["aff"] = g["aff"].fillna(0)
    g["pct"] = g["aff"] / g["total"] * 100
    years = sorted(g["year"].unique())
    w = 0.26

    fig, ax = plt.subplots(figsize=(11.5, 6))
    for j, conf in enumerate(CONFS):
        xs, vals = [], []
        for k, y in enumerate(years):
            row = g[(g["conf"] == conf) & (g["year"] == y)]
            if len(row):
                xs.append(k + (j - 1) * w)
                vals.append(float(row["pct"].iloc[0]))
        ax.bar(xs, vals, width=w, color=CONF_COLOR[conf], label=CONF_LABEL[conf])
        for x, v in zip(xs, vals):
            ax.text(x, v + 0.01, f"{v:.1f}", ha="center", va="bottom",
                    fontsize=7, color=INK2)
    ax.set_xticks(range(len(years)))
    ax.set_xticklabels(years)
    ax.set_ylabel("Org-affiliated safety papers,\n% of that venue's papers",
                  fontsize=11, color=INK2)
    ax.set_title("Org-affiliated AI-safety share by conference, by year",
                 fontsize=15, fontweight="bold", color=INK, pad=28)
    ax.text(0.0, 1.005, "A missing bar means that conference-year isn't covered. "
            f"Shown: {cov}.",
            transform=ax.transAxes, fontsize=8, color=INK2, va="bottom")
    style(ax)
    ax.legend(loc="upper left", fontsize=10, frameon=False)
    fig.tight_layout()
    fig.savefig(OUT / "org_share_by_conf.png", dpi=150, bbox_inches="tight",
                facecolor="white")
    plt.close(fig)
    print(f"Saved: {OUT/'org_share_by_conf.png'}")


def plot_composition(org, order, colors):
    ns = org.groupby("year").size()
    years = sorted(y for y in org["year"].unique() if ns[y] >= 10)  # skip 1-2 paper yrs
    org = org[org["year"].isin(years)]
    ct = (org.groupby(["year", "subdomain"]).size().unstack(fill_value=0)
          .reindex(columns=order, fill_value=0))
    share = ct.div(ct.sum(axis=1), axis=0) * 100

    fig, ax = plt.subplots(figsize=(12, 7))
    for name in order:
        ax.plot(years, share[name], marker="o", ms=4, lw=1.8,
                color=colors[name], label=name)
    ax.set_xticks(years)
    ax.set_xticklabels(years)
    ax.set_ylabel("Share of that year's org-affiliated papers (%)",
                  fontsize=11, color=INK2)
    ax.set_title("Composition of org-affiliated AI-safety research, over time",
                 fontsize=15, fontweight="bold", color=INK, pad=28)
    ax.text(0.0, 1.005, "Each line is a subdomain's share of that year's org-affiliated "
            "papers (they sum to 100%). Years with fewer than 10 papers omitted.  " +
            "  ".join(f"{y}: n={ns[y]}" for y in years),
            transform=ax.transAxes, fontsize=7.5, color=INK2, va="bottom")
    style(ax)
    ax.set_ylim(bottom=0)
    ax.legend(loc="center left", bbox_to_anchor=(1.005, 0.5), fontsize=8.5,
              frameon=False, title="Subdomain", title_fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / "org_areas_composition.png", dpi=150, bbox_inches="tight",
                facecolor="white")
    plt.close(fig)
    print(f"Saved: {OUT/'org_areas_composition.png'}")


def plot_all_years(org, order, colors):
    counts = org["subdomain"].value_counts().reindex(order).fillna(0).astype(int)
    names = counts.index[::-1]
    vals = counts.values[::-1]

    fig, ax = plt.subplots(figsize=(9, 7))
    ax.barh(names, vals, color=[colors[n] for n in names],
            edgecolor="white", linewidth=0.7)
    for i, v in enumerate(vals):
        if v:
            ax.text(v + max(vals) * 0.008, i, str(v), va="center",
                    fontsize=9.5, fontweight="bold", color=INK)
    ax.set_xlim(0, max(vals) * 1.10)
    ax.set_xlabel("Org-affiliated safety papers (all venues, all years)",
                  fontsize=11, color=INK2)
    ax.set_title("Org-affiliated AI-safety papers by subdomain — all years",
                 fontsize=14.5, fontweight="bold", color=INK, pad=12)
    ax.tick_params(axis="y", labelsize=10)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.grid(axis="x", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(OUT / "org_subdomains_all_years.png", dpi=150,
                bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Saved: {OUT/'org_subdomains_all_years.png'}")


def plot_per_year(org, order, colors):
    rev = order[::-1]  # smallest at bottom for barh
    years = sorted(org["year"].unique())
    ncol = 4
    nrow = -(-len(years) // ncol)
    fig, axes = plt.subplots(nrow, ncol, figsize=(4.2 * ncol, 3.4 * nrow),
                             sharey=True)
    axes = axes.ravel()
    for ax, y in zip(axes, years):
        sy = org[org["year"] == y]
        counts = sy["subdomain"].value_counts().reindex(rev, fill_value=0)
        ax.barh(rev, counts.values, color=[colors[n] for n in rev],
                edgecolor="white", linewidth=0.5)
        mx = max(counts.values) if counts.values.max() else 1
        for i, v in enumerate(counts.values):
            if v:
                ax.text(v + mx * 0.02, i, str(v), va="center", fontsize=7.5,
                        color=INK)
        ax.set_xlim(0, mx * 1.16)
        ax.set_title(f"{y}   (n={len(sy)})", fontsize=11, fontweight="bold",
                     color=INK)
        ax.tick_params(axis="y", labelsize=7.5)
        ax.tick_params(axis="x", labelsize=8)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        ax.grid(axis="x", color=GRID, lw=0.7)
        ax.set_axisbelow(True)
    for ax in axes[len(years):]:
        ax.set_visible(False)
    fig.suptitle("Org-affiliated AI-safety papers by subdomain, per year",
                 fontsize=15, fontweight="bold", color=INK, y=1.005)
    fig.tight_layout()
    fig.savefig(OUT / "org_subdomains_per_year.png", dpi=150,
                bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Saved: {OUT/'org_subdomains_per_year.png'}")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    res = load_results()
    order, colors = subdomain_palette(res)
    org, tot, covered = org_frame(res)
    cov = covered_str(covered)
    print(f"{len(org)} org-affiliated safety papers over "
          f"{len(covered)} covered conf-years: {cov}")
    plot_share_by_year(org, tot, cov)
    plot_share_by_conf(org, tot, cov)
    plot_composition(org, order, colors)
    plot_all_years(org, order, colors)
    plot_per_year(org, order, colors)


if __name__ == "__main__":
    main()
