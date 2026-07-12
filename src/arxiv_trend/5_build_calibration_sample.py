#!/usr/bin/env python3
"""
Build a large RANDOM sample of arXiv papers for arXiv-native threshold
calibration. arXiv is its own distribution (more recent, includes
preprints/workshop/rejected work), so the operating threshold must be set from
random arXiv papers labelled by DeepSeek — not from conference data.

Reuses any papers already labelled in calibration/sample_deepseek.csv so we only
pay to label the new ones. Writes:
  calibration/random_sample.csv       the full N-paper random set (ids + text)
  calibration/random_to_label.csv     only the not-yet-labelled subset (for classify.py)
"""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
ARXIV = ROOT / "data" / "arxiv"
CAL = ARXIV / "calibration"

N_RANDOM = 3000
SEED = 123


def main():
    CAL.mkdir(parents=True, exist_ok=True)
    papers = pd.read_csv(ARXIV / "papers.csv", dtype=str)[["id", "title", "abstract"]]
    preds = pd.read_csv(ARXIV / "predictions.csv", dtype={"id": str})
    df = papers.merge(preds[["id", "proba"]], on="id", how="inner")
    df["proba"] = df["proba"].astype(float)

    sample = df.sample(n=N_RANDOM, random_state=SEED).reset_index(drop=True)
    sample.to_csv(CAL / "random_sample.csv", index=False)

    # Which of these already have DeepSeek labels (from the earlier run)?
    already = set()
    prev = CAL / "random_labeled.csv"
    if prev.exists():
        already = set(pd.read_csv(prev, dtype={"id": str})["id"])
    to_label = sample[~sample["id"].isin(already)][["id", "title", "abstract"]]
    to_label.to_csv(CAL / "random_to_label.csv", index=False)

    print(f"Random sample: {len(sample)} papers")
    print(f"Already labelled (reused): {len(sample) - len(to_label)}")
    print(f"To label now: {len(to_label)}  (~${len(to_label)*0.0004:.2f})")
    print(f"Saved: {CAL/'random_sample.csv'}, {CAL/'random_to_label.csv'}")


if __name__ == "__main__":
    main()
