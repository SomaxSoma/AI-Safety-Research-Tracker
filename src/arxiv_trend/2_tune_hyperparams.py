#!/usr/bin/env python3
"""
Grid-search TF-IDF + linear-classifier hyperparameters for the safety detector.

Optimises PR-AUC (average precision) with stratified 4-fold CV, which is the
right target for an imbalanced (~4% positive) problem. The vectorizer is cached
via the Pipeline `memory` arg so it isn't refit when only the classifier
changes. The winning config is then evaluated on the TEMPORAL split
(train<=2024 / test 2025-26) to confirm it generalises across time, not just in
random CV.
"""

import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import GridSearchCV, StratifiedKFold
from sklearn.pipeline import Pipeline

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"


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
            frames.append(m[["title", "abstract", "is_safety", "year"]])
    df = pd.concat(frames, ignore_index=True)
    df["is_safety"] = df["is_safety"].astype(str).str.lower().isin(["true", "1"])
    df["text"] = (df["title"].fillna("") + ". " + df["abstract"].fillna("")).str.strip()
    return df[df["text"].str.len() > 20].reset_index(drop=True)


def main():
    df = load_labeled()
    y = df["is_safety"].values.astype(int)
    print(f"Loaded {len(df)} papers, {y.sum()} safety ({y.mean()*100:.2f}%)\n")

    cachedir = tempfile.mkdtemp()
    pipe = Pipeline([
        ("tfidf", TfidfVectorizer(strip_accents="unicode", stop_words="english",
                                  sublinear_tf=True, lowercase=True)),
        ("clf", LogisticRegression(class_weight="balanced", max_iter=3000, solver="liblinear")),
    ], memory=cachedir)

    param_grid = {
        "tfidf__ngram_range": [(1, 1), (1, 2)],   # trigrams dropped: slow, rarely help
        "tfidf__min_df": [2, 3, 5],
        "tfidf__max_df": [0.9],
        "tfidf__max_features": [100_000],
        "clf__C": [1, 10, 100],
    }

    cv = StratifiedKFold(n_splits=4, shuffle=True, random_state=42)
    # n_jobs=2 (not -1): each worker builds a ~0.5-1GB TF-IDF matrix and the
    # machine only has ~5GB free, so more workers OOM.
    gs = GridSearchCV(pipe, param_grid, scoring="average_precision",
                      cv=cv, n_jobs=2, verbose=2, refit=True)
    gs.fit(df["text"], y)

    print("\n" + "=" * 60)
    print("TOP 8 CONFIGS BY CV PR-AUC")
    print("=" * 60)
    res = pd.DataFrame(gs.cv_results_)
    cols = ["mean_test_score", "std_test_score",
            "param_tfidf__ngram_range", "param_tfidf__min_df", "param_clf__C"]
    top = res.sort_values("mean_test_score", ascending=False)[cols].head(8)
    for _, r in top.iterrows():
        print(f"  PR-AUC={r['mean_test_score']:.4f} ±{r['std_test_score']:.4f}  "
              f"ngram={r['param_tfidf__ngram_range']} min_df={r['param_tfidf__min_df']} "
              f"C={r['param_clf__C']}")

    print(f"\nBEST CV PR-AUC: {gs.best_score_:.4f}")
    print(f"BEST PARAMS: {gs.best_params_}")

    # --- Evaluate winner on the temporal split ---
    tr = df.index[df["year"] <= 2024].values
    te = df.index[df["year"] >= 2025].values
    best = gs.best_estimator_
    best.fit(df.loc[tr, "text"], y[tr])
    proba = best.predict_proba(df.loc[te, "text"])[:, 1]
    print("\n" + "=" * 60)
    print("WINNER ON TEMPORAL SPLIT (train<=2024, test 2025-26)")
    print("=" * 60)
    print(f"  ROC-AUC={roc_auc_score(y[te], proba):.4f}  PR-AUC={average_precision_score(y[te], proba):.4f}")
    print("  (baseline hand-tuned config was ROC-AUC=0.968, PR-AUC=0.784)")


if __name__ == "__main__":
    main()
