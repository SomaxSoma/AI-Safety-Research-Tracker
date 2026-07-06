#!/usr/bin/env python3
"""
Tune the classifier decision threshold to make its YEARLY safety-prevalence
estimate match the true yearly prevalence, in log space.

Objective (minimised over the threshold t):

    L(t) = mean_over_years [ ( log(pred_frac(year, t)) - log(true_frac(year)) )^2 ]

where
    pred_frac(year, t) = fraction of that year's papers with p_safety >= t
    true_frac(year)    = fraction of that year's papers actually labelled safety

Log space means relative error is penalised equally across the whole range
(the trend spans ~0.3% in 2019 to ~9% in 2026), which is what we want for a
prevalence trend rather than per-paper accuracy.

Predicted fractions are computed from OUT-OF-FOLD probabilities
(cross_val_predict) so no paper is scored by a model trained on it — otherwise
the in-sample fractions would look artificially perfect.

Writes the tuned threshold back into data/model/safety_tfidf.pkl and saves a
diagnostic plot data/model/threshold_tuning.png.
"""

from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import Pipeline

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = DATA / "model"

# Best config (updated from the grid search in tune_safety_clf.py).
VECTORIZER_PARAMS = dict(
    lowercase=True, strip_accents="unicode", stop_words="english",
    ngram_range=(1, 2), min_df=5, max_df=0.9, sublinear_tf=True,
    max_features=100_000,
)
CLF_PARAMS = dict(class_weight="balanced", C=10, max_iter=3000, solver="liblinear")


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


def yearly_log_mse(df, proba, thr, years, true_frac):
    """The user's objective at a single threshold."""
    errs = []
    for yr in years:
        mask = df["year"].values == yr
        n = mask.sum()
        pred_frac = (proba[mask] >= thr).mean()
        # Clamp a zero predicted fraction to "less than half a paper" so log is finite.
        pred_frac = max(pred_frac, 0.5 / n)
        errs.append((np.log(pred_frac) - np.log(true_frac[yr])) ** 2)
    return float(np.mean(errs))


def main():
    df = load_labeled()
    y = df["is_safety"].values.astype(int)
    years = sorted(df["year"].unique())
    true_frac = {yr: df.loc[df["year"] == yr, "is_safety"].mean() for yr in years}
    print(f"Loaded {len(df)} papers over years {years[0]}-{years[-1]}")
    print("True yearly safety fraction:")
    for yr in years:
        print(f"  {yr}: {true_frac[yr]*100:.2f}%")

    # Out-of-fold probabilities so per-year predicted fractions are honest.
    pipe = Pipeline([
        ("tfidf", TfidfVectorizer(**VECTORIZER_PARAMS)),
        ("clf", LogisticRegression(**CLF_PARAMS)),
    ])
    print("\nComputing out-of-fold probabilities (5-fold)...")
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    # n_jobs=2 to stay within ~5GB RAM (each worker holds a big TF-IDF matrix).
    proba = cross_val_predict(pipe, df["text"], y, cv=cv,
                              method="predict_proba", n_jobs=2)[:, 1]

    # Sweep thresholds.
    thresholds = np.linspace(0.02, 0.95, 187)
    losses = np.array([yearly_log_mse(df, proba, t, years, true_frac) for t in thresholds])
    best_i = int(np.argmin(losses))
    t_star = float(thresholds[best_i])
    print(f"\nOptimal threshold: {t_star:.3f}  (log-MSE loss = {losses[best_i]:.4f})")

    # Compare with the F1-optimal 0.446 baseline.
    for label, t in [("log-MSE optimal", t_star), ("F1-optimal (0.446)", 0.446), ("0.5", 0.5)]:
        print(f"\n  {label} (thr={t:.3f}):  loss={yearly_log_mse(df, proba, t, years, true_frac):.4f}")
        for yr in years:
            mask = df["year"].values == yr
            pf = (proba[mask] >= t).mean()
            print(f"     {yr}: pred {pf*100:5.2f}%  vs true {true_frac[yr]*100:5.2f}%")

    # --- Diagnostic plot ---
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5))

    ax1.plot(thresholds, losses, color="#4e79a7", lw=2)
    ax1.axvline(t_star, color="#e15759", ls="--", lw=1.5,
                label=f"optimal = {t_star:.3f}")
    ax1.axvline(0.446, color="#999", ls=":", lw=1.5, label="F1-opt = 0.446")
    ax1.set_xlabel("Threshold", fontsize=11)
    ax1.set_ylabel("Yearly log-prevalence MSE", fontsize=11)
    ax1.set_title("Threshold objective\nmean_year (log pred − log true)²",
                  fontsize=12, fontweight="bold")
    ax1.legend(fontsize=10, frameon=False)
    ax1.spines["top"].set_visible(False); ax1.spines["right"].set_visible(False)

    pred_at_star = [(proba[df["year"].values == yr] >= t_star).mean() * 100 for yr in years]
    true_pct = [true_frac[yr] * 100 for yr in years]
    ax2.plot(years, true_pct, "o-", color="#59a14f", lw=2, label="true (DeepSeek labels)")
    ax2.plot(years, pred_at_star, "s--", color="#e15759", lw=2,
             label=f"predicted @ thr={t_star:.3f}")
    ax2.set_yscale("log")
    ax2.set_xlabel("Year", fontsize=11)
    ax2.set_ylabel("Safety-paper fraction (%, log scale)", fontsize=11)
    ax2.set_title("Fit at optimal threshold", fontsize=12, fontweight="bold")
    ax2.legend(fontsize=10, frameon=False)
    ax2.spines["top"].set_visible(False); ax2.spines["right"].set_visible(False)

    fig.tight_layout()
    fig.savefig(OUT / "threshold_tuning.png", dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"\nSaved: {OUT/'threshold_tuning.png'}")

    # --- Update saved model with the tuned threshold ---
    model_path = OUT / "safety_tfidf.pkl"
    if model_path.exists():
        bundle = joblib.load(model_path)
        bundle["threshold_f1"] = bundle.get("threshold")
        bundle["threshold"] = t_star
        bundle["threshold_objective"] = "yearly_log_prevalence_mse"
        joblib.dump(bundle, model_path)
        print(f"Updated {model_path} operating threshold -> {t_star:.3f}")


if __name__ == "__main__":
    main()
