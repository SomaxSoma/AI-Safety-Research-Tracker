#!/usr/bin/env python3
"""
Apply the trained TF-IDF safety classifier to the fetched arXiv abstracts.

Reads:  data/arxiv/papers.csv   (from fetch_arxiv.py)
        data/model/safety_tfidf.pkl
Writes: data/arxiv/predictions.csv  (id, month, primary_category, proba, is_safety_pred)
"""

import argparse
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
ARXIV = ROOT / "data" / "arxiv"
MODEL = ROOT / "data" / "model" / "safety_tfidf.pkl"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=str(ARXIV / "papers.csv"))
    ap.add_argument("--output", default=str(ARXIV / "predictions.csv"))
    ap.add_argument("--threshold", type=float, default=None,
                    help="Override the model's saved operating threshold")
    args = ap.parse_args()

    bundle = joblib.load(MODEL)
    vec, clf = bundle["vectorizer"], bundle["classifier"]
    thr = args.threshold if args.threshold is not None else bundle["threshold"]
    print(f"Model threshold: {thr:.3f} (objective: {bundle.get('threshold_objective','?')})")

    df = pd.read_csv(args.input, dtype=str)
    df["text"] = (df["title"].fillna("") + ". " + df["abstract"].fillna("")).str.strip()
    ok = df["text"].str.len() > 20
    print(f"Loaded {len(df)} arXiv papers ({(~ok).sum()} with too-short text skipped)")
    df = df[ok].reset_index(drop=True)

    # Classify in chunks to bound peak memory (RAM-constrained machine).
    proba = np.empty(len(df), dtype=np.float32)
    CHUNK = 20000
    for i in range(0, len(df), CHUNK):
        X = vec.transform(df["text"].iloc[i:i + CHUNK])
        proba[i:i + CHUNK] = clf.predict_proba(X)[:, 1]
        print(f"  classified {min(i+CHUNK, len(df))}/{len(df)}")

    df["proba"] = proba
    df["is_safety_pred"] = (proba >= thr).astype(int)
    # Month from the submission date (published = v1 date).
    df["ym"] = pd.to_datetime(df["published"], errors="coerce").dt.strftime("%Y-%m")

    out = df[["id", "ym", "primary_category", "proba", "is_safety_pred"]]
    out.to_csv(args.output, index=False)

    n_safe = int(df["is_safety_pred"].sum())
    print(f"\nSafety-classified: {n_safe} / {len(df)} ({n_safe/len(df)*100:.2f}%)")
    print(f"Saved: {args.output}")


if __name__ == "__main__":
    main()
