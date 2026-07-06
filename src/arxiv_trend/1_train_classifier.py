#!/usr/bin/env python3
"""
Train a TF-IDF + Logistic Regression classifier to detect AI-safety papers
from title + abstract text.

Labels come from the DeepSeek classification (results.csv):
  positive = is_safety (Class 4)
  negative = everything else (Classes 1/2/3 — includes ethics/fairness and
             truthfulness/reliability, which count as NON-safety here)

Evaluates on:
  - a random stratified 80/20 split
  - a temporal split (train <= 2024, test 2025-2026) to check that the model
    generalises across time rather than memorising a static vocabulary

Outputs (under data/model/):
  safety_tfidf.pkl     the fitted pipeline (vectorizer + classifier + threshold)
  roc_curve.png        ROC curves for both splits
  pr_curve.png         precision-recall curves for both splits
  metrics.json         summary metrics
"""

import json
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (auc, average_precision_score,
                             precision_recall_curve, precision_recall_fscore_support,
                             roc_auc_score, roc_curve)
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
OUT = DATA / "model"

VECTORIZER_PARAMS = dict(
    lowercase=True, strip_accents="unicode", stop_words="english",
    ngram_range=(1, 2), min_df=5, max_df=0.9, sublinear_tf=True,
    max_features=100_000,
)
CLF_PARAMS = dict(class_weight="balanced", C=10, max_iter=2000, solver="liblinear")


def load_labeled() -> pd.DataFrame:
    frames = []
    for conf in ["iclr", "icml", "neurips"]:
        cdir = DATA / conf
        if not cdir.exists():
            continue
        for yd in sorted(cdir.iterdir()):
            r, p = yd / "results.csv", yd / "papers.csv"
            if not (r.exists() and p.exists()):
                continue
            res = pd.read_csv(r, dtype={"id": str})
            pap = pd.read_csv(p, dtype={"id": str})
            res["class"] = pd.to_numeric(res["class"], errors="coerce").fillna(3).astype(int)
            m = res.merge(pap[["id", "abstract"]], on="id", how="left")
            m["year"] = int(yd.name)
            m["conference"] = conf
            frames.append(m[["id", "title", "abstract", "is_safety", "year", "conference"]])
    df = pd.concat(frames, ignore_index=True)
    df["is_safety"] = df["is_safety"].astype(str).str.lower().isin(["true", "1"])
    df["text"] = (df["title"].fillna("") + ". " + df["abstract"].fillna("")).str.strip()
    df = df[df["text"].str.len() > 20].reset_index(drop=True)
    return df


def fit_split(df, train_idx, test_idx):
    vec = TfidfVectorizer(**VECTORIZER_PARAMS)
    Xtr = vec.fit_transform(df.loc[train_idx, "text"])
    Xte = vec.transform(df.loc[test_idx, "text"])
    y = df["is_safety"].values.astype(int)
    clf = LogisticRegression(**CLF_PARAMS)
    clf.fit(Xtr, y[train_idx])
    proba = clf.predict_proba(Xte)[:, 1]
    return vec, clf, proba, y[test_idx]


def f1_optimal_threshold(y_true, proba):
    prec, rec, thr = precision_recall_curve(y_true, proba)
    f1s = 2 * prec * rec / (prec + rec + 1e-12)
    best = int(np.argmax(f1s))
    return float(thr[best]) if best < len(thr) else 0.5


def summarize(y_true, proba, name):
    thr = f1_optimal_threshold(y_true, proba)
    pred = (proba >= thr).astype(int)
    p, r, f, _ = precision_recall_fscore_support(y_true, pred, average="binary", zero_division=0)
    m = {
        "split": name,
        "n_test": int(len(y_true)),
        "n_pos": int(y_true.sum()),
        "roc_auc": float(roc_auc_score(y_true, proba)),
        "pr_auc": float(average_precision_score(y_true, proba)),
        "f1_opt_threshold": thr,
        "precision": float(p), "recall": float(r), "f1": float(f),
        "true_prevalence_pct": float(y_true.mean() * 100),
        "predcount_prevalence_pct": float(pred.mean() * 100),
        "probmass_prevalence_pct": float(proba.mean() * 100),
    }
    print(f"\n=== {name} (n={m['n_test']}, pos={m['n_pos']}) ===")
    print(f"  ROC-AUC={m['roc_auc']:.3f}  PR-AUC={m['pr_auc']:.3f}")
    print(f"  @thr={thr:.3f}: P={p:.3f} R={r:.3f} F1={f:.3f}")
    print(f"  prevalence: true={m['true_prevalence_pct']:.2f}%  "
          f"pred-count={m['predcount_prevalence_pct']:.2f}%  "
          f"prob-mass={m['probmass_prevalence_pct']:.2f}%")
    return m


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    df = load_labeled()
    y = df["is_safety"].values.astype(int)
    print(f"Loaded {len(df)} papers, {y.sum()} safety ({y.mean()*100:.2f}%)")

    splits = {}
    # Random stratified 80/20
    tr, te = train_test_split(np.arange(len(df)), test_size=0.2, stratify=y, random_state=42)
    _, _, proba_r, yte_r = fit_split(df, tr, te)
    splits["random"] = (yte_r, proba_r)

    # Temporal: train <=2024, test 2025-2026
    tr_t = df.index[df["year"] <= 2024].values
    te_t = df.index[df["year"] >= 2025].values
    _, _, proba_t, yte_t = fit_split(df, tr_t, te_t)
    splits["temporal"] = (yte_t, proba_t)

    metrics = [
        summarize(yte_r, proba_r, "random_80_20"),
        summarize(yte_t, proba_t, "temporal_train<=2024_test2025-26"),
    ]

    # --- ROC curve ---
    fig, ax = plt.subplots(figsize=(6.5, 6))
    for (name, (yt, pr)), color in zip(
            [("Random 80/20", splits["random"]),
             ("Temporal (test 2025-26)", splits["temporal"])],
            ["#4e79a7", "#e15759"]):
        fpr, tpr, _ = roc_curve(yt, pr)
        ax.plot(fpr, tpr, color=color, lw=2,
                label=f"{name}  (AUC={auc(fpr, tpr):.3f})")
    ax.plot([0, 1], [0, 1], "--", color="#999", lw=1, label="Chance")
    ax.set_xlabel("False Positive Rate", fontsize=11)
    ax.set_ylabel("True Positive Rate", fontsize=11)
    ax.set_title("Safety Classifier ROC — TF-IDF + Logistic Regression",
                 fontsize=13, fontweight="bold", pad=12)
    ax.legend(loc="lower right", fontsize=10, frameon=False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_xlim(-0.01, 1.01); ax.set_ylim(-0.01, 1.01)
    fig.tight_layout()
    fig.savefig(OUT / "roc_curve.png", dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"\nSaved: {OUT/'roc_curve.png'}")

    # --- PR curve ---
    fig, ax = plt.subplots(figsize=(6.5, 6))
    for (name, (yt, pr)), color in zip(
            [("Random 80/20", splits["random"]),
             ("Temporal (test 2025-26)", splits["temporal"])],
            ["#4e79a7", "#e15759"]):
        prec, rec, _ = precision_recall_curve(yt, pr)
        ax.plot(rec, prec, color=color, lw=2,
                label=f"{name}  (AP={average_precision_score(yt, pr):.3f})")
        ax.axhline(yt.mean(), ls=":", color=color, lw=1, alpha=0.6)
    ax.set_xlabel("Recall", fontsize=11)
    ax.set_ylabel("Precision", fontsize=11)
    ax.set_title("Safety Classifier Precision-Recall\n(dotted = base rate)",
                 fontsize=13, fontweight="bold", pad=12)
    ax.legend(loc="upper right", fontsize=10, frameon=False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_xlim(-0.01, 1.01); ax.set_ylim(-0.01, 1.01)
    fig.tight_layout()
    fig.savefig(OUT / "pr_curve.png", dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Saved: {OUT/'pr_curve.png'}")

    # --- Fit final model on ALL data and persist ---
    vec = TfidfVectorizer(**VECTORIZER_PARAMS)
    X = vec.fit_transform(df["text"])
    clf = LogisticRegression(**CLF_PARAMS)
    clf.fit(X, y)
    # Use the temporal-split F1-optimal threshold as the operating point, since
    # applying to future/arxiv data is the temporal-generalisation scenario.
    thr = f1_optimal_threshold(yte_t, proba_t)
    joblib.dump({"vectorizer": vec, "classifier": clf, "threshold": thr,
                 "vectorizer_params": VECTORIZER_PARAMS, "clf_params": CLF_PARAMS},
                OUT / "safety_tfidf.pkl")
    print(f"Saved: {OUT/'safety_tfidf.pkl'} (operating threshold={thr:.3f})")

    (OUT / "metrics.json").write_text(json.dumps(metrics, indent=2))
    print(f"Saved: {OUT/'metrics.json'}")

    # Top predictive terms (interpretability sanity check)
    names = np.array(vec.get_feature_names_out())
    coefs = clf.coef_[0]
    top_pos = names[np.argsort(coefs)[-25:][::-1]]
    print("\nTop 25 safety-indicative terms:")
    print("  " + ", ".join(top_pos))


if __name__ == "__main__":
    main()
