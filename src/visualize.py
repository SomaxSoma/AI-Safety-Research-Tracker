#!/usr/bin/env python3
"""Generate plots and filtered CSVs from classification results."""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

DATA_ROOT = Path(__file__).resolve().parent.parent / "data"

CLASS_LABELS = {
    1: "Ethics &\nFairness",
    2: "Truthfulness &\nReliability",
    3: "General\nCapabilities",
    4: "AI Safety",
}

SUBAREA_LABELS = {
    "A": "Interpretability &\nUnderstanding",
    "B": "Scalable Oversight &\nValue Learning",
    "C": "Agent Foundations &\nAlignment Theory",
    "D": "Threat Modeling &\nEvaluations",
    "E": "Capability Control &\nUnlearning",
    "F": "Robustness, Defense &\nSystemic Control",
    "G": "Technical Governance\n& Policy",
}

SUBDOMAIN_TO_SUBAREA = {
    "Interpretability": "A",
    "Monitoring": "A",
    "Multi-Agent Safety": "B",
    "Scalable Oversight": "B",
    "Agent Foundations": "C",
    "Scheming and Deception": "D",
    "Dangerous Capability Evals": "D",
    "Biorisk": "D",
    "Safeguards": "D",
    "Model Organisms": "D",
    "Control": "D",
    "Alignment Training": "E",
    "Red-Teaming": "F",
    "Adversarial Robustness": "F",
    "Policy and Governance": "G",
    "Strategy and Forecasting": "G",
    "AI Welfare": "G",
}

COLORS_MAJOR   = ["#4e79a7", "#f28e2b", "#76b7b2", "#e15759"]
COLORS_SUBAREA = ["#59a14f", "#edc948", "#b07aa1", "#ff9da7", "#9c755f", "#bab0ac", "#86bcb6"]


def style_ax(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def plot_major(ax, names, counts):
    bars = ax.bar(names, counts, color=COLORS_MAJOR, edgecolor="white", linewidth=0.8)
    ax.set_title("Major Classification", fontsize=14, fontweight="bold", pad=12)
    ax.set_ylabel("Number of Papers", fontsize=11)
    for bar, val in zip(bars, counts):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 8, str(val),
                ha="center", va="bottom", fontsize=12, fontweight="bold")
    ax.set_ylim(0, max(counts) * 1.15)
    ax.tick_params(axis="x", labelsize=11)
    style_ax(ax)


def plot_subareas(ax, names, counts):
    bars = ax.barh(names[::-1], counts[::-1],
                   color=COLORS_SUBAREA[:len(counts)][::-1],
                   edgecolor="white", linewidth=0.8)
    ax.set_title("Safety Subareas", fontsize=14, fontweight="bold", pad=12)
    ax.set_xlabel("Number of Papers", fontsize=11)
    for bar, val in zip(bars, counts[::-1]):
        ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2, str(val),
                ha="left", va="center", fontsize=11, fontweight="bold")
    ax.set_xlim(0, max(counts) * 1.25)
    ax.tick_params(axis="y", labelsize=10)
    style_ax(ax)


def plot_detailed(ax, counts):
    colors = plt.cm.Set3(np.linspace(0, 1, max(len(counts), 1)))
    bars = ax.barh(counts.index[::-1], counts.values[::-1],
                   color=colors[::-1], edgecolor="white", linewidth=0.8)
    ax.set_title("Detailed Safety Classes", fontsize=14, fontweight="bold", pad=12)
    ax.set_xlabel("Number of Papers", fontsize=11)
    for bar, val in zip(bars, counts.values[::-1]):
        ax.text(bar.get_width() + 0.2, bar.get_y() + bar.get_height() / 2, str(val),
                ha="left", va="center", fontsize=11, fontweight="bold")
    ax.set_xlim(0, max(counts.values) * 1.25)
    ax.tick_params(axis="y", labelsize=10)
    style_ax(ax)


def plot_scores(ax, score_counts):
    bars = ax.bar(score_counts.index.astype(int), score_counts.values,
                  color="#7570b3", edgecolor="white", linewidth=0.8)
    ax.set_title("Safety-Relevance Score Distribution", fontsize=14, fontweight="bold", pad=12)
    ax.set_xlabel("Total Score (Motivation + Methodology + Evaluation)", fontsize=10)
    ax.set_ylabel("Number of Papers", fontsize=11)
    ax.set_xticks(range(1, 8))
    for bar, val in zip(bars, score_counts.values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3, str(val),
                ha="center", va="bottom", fontsize=11, fontweight="bold")
    ax.set_ylim(0, max(score_counts.values) * 1.2)
    style_ax(ax)


def render(df: pd.DataFrame, plots_dir: Path, filtered_dir: Path, dataset_label: str):
    plots_dir.mkdir(parents=True, exist_ok=True)
    filtered_dir.mkdir(parents=True, exist_ok=True)

    major_counts = df["class"].value_counts().sort_index()
    major_names  = [CLASS_LABELS[i] for i in major_counts.index]

    safety_df = df[df["is_safety"] == True].copy()
    safety_df["subarea"] = safety_df["subdomain"].map(SUBDOMAIN_TO_SUBAREA)

    present_subareas = [k for k in "ABCDEFG" if k in safety_df["subarea"].values]
    subarea_counts = safety_df["subarea"].value_counts().reindex(present_subareas, fill_value=0)
    subarea_names  = [SUBAREA_LABELS[k] for k in subarea_counts.index]
    subdomain_counts = safety_df["subdomain"].value_counts()
    score_counts = df[df["class"] == 4]["total_score"].value_counts().sort_index()

    plots = [
        ("major_classes.png", (7, 5), f"{dataset_label} — Major Classification",
         lambda ax: plot_major(ax, major_names, major_counts.values)),
        ("safety_subareas.png", (8, 5), f"{dataset_label} — Safety Subareas",
         lambda ax: plot_subareas(ax, subarea_names, subarea_counts.values)),
        ("detailed_classes.png", (8, 5), f"{dataset_label} — Detailed Safety Classes",
         lambda ax: plot_detailed(ax, subdomain_counts)),
        ("score_distribution.png", (7, 5), f"{dataset_label} — Safety Score Distribution",
         lambda ax: plot_scores(ax, score_counts)),
    ]
    for filename, size, title, draw in plots:
        fig, ax = plt.subplots(figsize=size)
        draw(ax)
        fig.suptitle(title, fontsize=15, fontweight="bold", y=0.98)
        fig.tight_layout(rect=[0, 0, 1, 0.95])
        path = plots_dir / filename
        fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        print(f"Saved: {path}")

    fig, axes = plt.subplots(1, 3, figsize=(22, 7), gridspec_kw={"width_ratios": [1, 1.2, 1.2]})
    plot_major(axes[0], major_names, major_counts.values)
    plot_subareas(axes[1], subarea_names, subarea_counts.values)
    plot_detailed(axes[2], subdomain_counts)
    fig.suptitle(f"{dataset_label} AI Safety Paper Classification", fontsize=17, fontweight="bold", y=0.99)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    overview_path = plots_dir / "overview.png"
    fig.savefig(overview_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Saved: {overview_path}")

    safety_out = safety_df[["title", "subdomain", "total_score"]].copy()
    safety_out["subarea"] = safety_df["subdomain"].map(SUBDOMAIN_TO_SUBAREA).map(
        lambda k: SUBAREA_LABELS.get(k, "").replace("\n", " "))
    safety_out = safety_out.rename(columns={
        "title": "Paper Title", "subarea": "Subarea",
        "subdomain": "Detailed Class", "total_score": "Score",
    })[["Paper Title", "Subarea", "Detailed Class", "Score"]]
    safety_path = filtered_dir / "safety.csv"
    safety_out.to_csv(safety_path, index=False)
    print(f"Saved: {safety_path} ({len(safety_out)} papers)")

    for cls, name in [(1, "ethics_fairness.csv"), (2, "truthfulness_reliability.csv")]:
        subset = df[df["class"] == cls][["title"]].rename(columns={"title": "Paper Title"})
        out_path = filtered_dir / name
        subset.to_csv(out_path, index=False)
        print(f"Saved: {out_path} ({len(subset)} papers)")


def main():
    parser = argparse.ArgumentParser(
        description="Generate plots and filtered CSVs from classification results",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
               "  python src/visualize.py iclr 2026\n"
               "  python src/visualize.py --input custom.csv --output-dir out/",
    )
    parser.add_argument("conference", nargs="?", help="Conference name (e.g. iclr, icml, neurips)")
    parser.add_argument("year", nargs="?", type=int, help="Conference year")
    parser.add_argument("--data-root", default=str(DATA_ROOT), help=f"Data root (default: {DATA_ROOT})")
    parser.add_argument("--input", help="Override results CSV path")
    parser.add_argument("--output-dir", help="Override output directory (plots/ and filtered/ written under it)")
    parser.add_argument("--label", help="Override dataset label shown in plot titles")
    args = parser.parse_args()

    if args.input and args.output_dir:
        input_path = Path(args.input)
        out_dir = Path(args.output_dir)
        label = args.label or input_path.stem
    elif args.conference and args.year:
        conf_dir = Path(args.data_root) / args.conference.lower() / str(args.year)
        input_path = Path(args.input) if args.input else conf_dir / "results.csv"
        out_dir = Path(args.output_dir) if args.output_dir else conf_dir
        label = args.label or f"{args.conference.upper()} {args.year}"
    else:
        parser.error("Provide either positional conference+year, or both --input and --output-dir")

    df = pd.read_csv(input_path)
    # Defensive: ensure class is int. Older CSVs may have stray text labels.
    df["class"] = pd.to_numeric(df["class"], errors="coerce").fillna(3).astype(int)
    render(df, out_dir / "plots", out_dir / "filtered", label)


if __name__ == "__main__":
    main()
