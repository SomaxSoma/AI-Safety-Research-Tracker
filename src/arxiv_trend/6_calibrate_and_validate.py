#!/usr/bin/env python3
"""
Does adding arXiv-labelled papers to the training set improve the classifier on
the arXiv domain?  Head-to-head, both evaluated honestly on the 3000 random
arXiv papers (DeepSeek-labelled):

  Model A  conference-only (the current saved model). It never trained on arXiv,
           so its predictions on the 3000 are already out-of-sample -> use the
           proba already in predictions.csv.
  Model B  conference + arXiv, evaluated by 5-fold CV over the 3000 arXiv papers
           (each fold trained on conference + the other 4 folds), so every
           arXiv prediction is out-of-fold.

Reports PR-AUC / ROC-AUC, and precision/recall at the threshold that matches the
DeepSeek arXiv prevalence, for both models.
"""

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
ARXIV = DATA / "arxiv"
CAL = ARXIV / "calibration"

VEC = dict(lowercase=True, strip_accents="unicode", stop_words="english",
           ngram_range=(1, 2), min_df=5, max_df=0.9, sublinear_tf=True, max_features=100_000)
CLF = dict(class_weight="balanced", C=10, max_iter=2000, solver="liblinear")


def load_conference():
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
            m = res.merge(pap[["id", "abstract"]], on="id", how="left")
            frames.append(m[["title", "abstract", "is_safety"]])
    df = pd.concat(frames, ignore_index=True)
    df["is_safety"] = df["is_safety"].astype(str).str.lower().isin(["true", "1"]).astype(int)
    df["text"] = (df["title"].fillna("") + ". " + df["abstract"].fillna("")).str.strip()
    return df[df["text"].str.len() > 20].reset_index(drop=True)


def load_arxiv_labeled():
    text = pd.read_csv(CAL / "random_sample.csv", dtype={"id": str})[["id", "title", "abstract"]]
    lab = pd.read_csv(CAL / "random_labeled.csv", dtype={"id": str})[["id", "is_safety"]]
    lab["y"] = lab["is_safety"].astype(str).str.lower().isin(["true", "1"]).astype(int)
    df = text.merge(lab[["id", "y"]], on="id", how="inner")
    preds = pd.read_csv(ARXIV / "predictions.csv", dtype={"id": str})[["id", "proba"]]
    df = df.merge(preds, on="id", how="left")   # proba = Model A (conference-only)
    df["proba"] = df["proba"].astype(float)
    df["text"] = (df["title"].fillna("") + ". " + df["abstract"].fillna("")).str.strip()
    return df.reset_index(drop=True)


def thr_matching_prevalence(proba, target):
    ts = np.linspace(0.2, 0.95, 301)
    prevs = np.array([(proba >= t).mean() for t in ts])
    return float(ts[int(np.argmin(np.abs(prevs - target)))])


def prec_recall_at(y, proba, thr):
    pred = (proba >= thr).astype(int)
    tp = int(((pred == 1) & (y == 1)).sum()); fp = int(((pred == 1) & (y == 0)).sum())
    fn = int(((pred == 0) & (y == 1)).sum())
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    return prec, rec, pred.mean()


def main():
    conf = load_conference()
    ax = load_arxiv_labeled()
    y_ax = ax["y"].values
    target = y_ax.mean()
    print(f"Conference: {len(conf)} papers ({conf['is_safety'].sum()} safety)")
    print(f"arXiv labelled: {len(ax)} papers ({y_ax.sum()} safety, prevalence {target*100:.2f}%)\n")

    # ---- Model A: conference-only, already-computed proba on the 3000 ----
    proba_A = ax["proba"].values

    # ---- Models B (equal weight) and B-w (arXiv upweighted): conference + arXiv,
    #      5-fold OOF over the arXiv papers ----
    ARXIV_WEIGHT = 15  # upweight so ~2400 arXiv rows ~ conference influence
    proba_B = np.zeros(len(ax))
    proba_Bw = np.zeros(len(ax))
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    n_conf = len(conf)
    for k, (tr, te) in enumerate(skf.split(ax["text"], y_ax), 1):
        train_text = pd.concat([conf["text"], ax["text"].iloc[tr]], ignore_index=True)
        train_y = np.concatenate([conf["is_safety"].values, y_ax[tr]])
        vec = TfidfVectorizer(**VEC)
        Xtr = vec.fit_transform(train_text)
        Xte = vec.transform(ax["text"].iloc[te])
        # equal weight
        clf = LogisticRegression(**CLF).fit(Xtr, train_y)
        proba_B[te] = clf.predict_proba(Xte)[:, 1]
        # arXiv upweighted
        w = np.concatenate([np.ones(n_conf), np.full(len(tr), ARXIV_WEIGHT)])
        clfw = LogisticRegression(**CLF).fit(Xtr, train_y, sample_weight=w)
        proba_Bw[te] = clfw.predict_proba(Xte)[:, 1]
        print(f"  fold {k}/5 done")

    print("\n" + "=" * 56)
    print("HEAD-TO-HEAD on 3000 random arXiv (DeepSeek labels)")
    print("=" * 56)
    for name, proba in [("A: conference-only", proba_A),
                        ("B: conference+arXiv (equal)", proba_B),
                        (f"B-w: conference+arXiv (x{ARXIV_WEIGHT})", proba_Bw)]:
        prauc = average_precision_score(y_ax, proba)
        rocauc = roc_auc_score(y_ax, proba)
        t = thr_matching_prevalence(proba, target)
        p, r, pv = prec_recall_at(y_ax, proba, t)
        print(f"\n{name}")
        print(f"  PR-AUC={prauc:.3f}  ROC-AUC={rocauc:.3f}")
        print(f"  @prevalence-matched thr={t:.3f}: precision={p:.3f} recall={r:.3f} "
              f"(pred prev {pv*100:.2f}% vs true {target*100:.2f}%)")


if __name__ == "__main__":
    main()
