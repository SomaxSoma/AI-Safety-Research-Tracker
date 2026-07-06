#!/usr/bin/env python3
"""
Compare the TF-IDF classifier against DeepSeek labels on the arXiv calibration
sample, to check the classifier transfers from conference papers to arXiv.

  - random stratum -> unbiased prevalence calibration (does TF-IDF's safety rate
    match DeepSeek's on a representative arXiv slice?) and recall.
  - tfidf_pos stratum -> precision (of papers TF-IDF flags, how many does
    DeepSeek confirm?).
"""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CAL = ROOT / "data" / "arxiv" / "calibration"


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / denom
    return (max(0, centre - half), min(1, centre + half))


def main():
    sample = pd.read_csv(CAL / "sample.csv", dtype={"id": str})
    ds = pd.read_csv(CAL / "sample_deepseek.csv", dtype={"id": str})
    ds["ds_safety"] = ds["is_safety"].astype(str).str.lower().isin(["true", "1"]).astype(int)
    df = sample.merge(ds[["id", "ds_safety"]], on="id", how="inner")
    df["tfidf_pred"] = df["tfidf_pred"].astype(int)
    print(f"Merged {len(df)} labelled papers\n")

    rnd = df[df["stratum"] == "random"]
    pos = df[df["stratum"] == "tfidf_pos"]

    # --- Prevalence calibration on the random slice ---
    ds_prev = rnd["ds_safety"].mean()
    tf_prev = rnd["tfidf_pred"].mean()
    lo, hi = wilson(rnd["ds_safety"].sum(), len(rnd))
    print("PREVALENCE (random slice, unbiased):")
    print(f"  DeepSeek 'ground truth': {ds_prev*100:.2f}%  (95% CI {lo*100:.2f}-{hi*100:.2f}%, n={len(rnd)})")
    print(f"  TF-IDF classifier:       {tf_prev*100:.2f}%")
    print(f"  -> classifier is {'within' if lo <= tf_prev <= hi else 'OUTSIDE'} the DeepSeek CI\n")

    # --- Precision from the positive stratum (dedup any that were also random) ---
    # Use every predicted-positive paper in the whole sample for precision.
    predpos = df[df["tfidf_pred"] == 1]
    prec = predpos["ds_safety"].mean()
    plo, phi = wilson(predpos["ds_safety"].sum(), len(predpos))
    print(f"PRECISION (of {len(predpos)} TF-IDF positives, DeepSeek confirms):")
    print(f"  {prec*100:.1f}%  (95% CI {plo*100:.1f}-{phi*100:.1f}%)\n")

    # --- Recall from the random slice (representative positives) ---
    rnd_pos = rnd[rnd["ds_safety"] == 1]
    if len(rnd_pos) > 0:
        rec = rnd_pos["tfidf_pred"].mean()
        rlo, rhi = wilson(rnd_pos["tfidf_pred"].sum(), len(rnd_pos))
        print(f"RECALL (of {len(rnd_pos)} DeepSeek-positive in random slice, TF-IDF caught):")
        print(f"  {rec*100:.1f}%  (95% CI {rlo*100:.1f}-{rhi*100:.1f}%)\n")

    # --- Confusion matrix over the whole sample ---
    print("CONFUSION (whole sample, rows=DeepSeek, cols=TF-IDF):")
    ct = pd.crosstab(df["ds_safety"].map({1: "safety", 0: "non-safety"}),
                     df["tfidf_pred"].map({1: "pred safety", 0: "pred non"}))
    print(ct.to_string())

    agree = (df["ds_safety"] == df["tfidf_pred"]).mean()
    print(f"\nRaw agreement: {agree*100:.1f}%")

    # --- Disagreements to eyeball ---
    fn = df[(df["ds_safety"] == 1) & (df["tfidf_pred"] == 0)]
    fp = df[(df["ds_safety"] == 0) & (df["tfidf_pred"] == 1)]
    print(f"\nDeepSeek-safety but TF-IDF missed (FN): {len(fn)}")
    for _, r in fn.head(6).iterrows():
        print(f"   [{r['tfidf_proba']:.2f}] {r['title'][:75]}")
    print(f"\nTF-IDF-safety but DeepSeek non (FP): {len(fp)}")
    for _, r in fp.head(6).iterrows():
        print(f"   [{r['tfidf_proba']:.2f}] {r['title'][:75]}")


if __name__ == "__main__":
    main()
