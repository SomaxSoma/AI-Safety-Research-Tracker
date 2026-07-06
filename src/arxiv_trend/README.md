# arXiv AI-Safety Trend Experiment

Estimates the monthly share of arXiv ML papers that are AI-safety research,
2019–2026, by combining an **LLM classifier** (DeepSeek, accurate but too
expensive for ~400k papers) with a cheap **TF-IDF classifier** trained to mimic
it, then **calibrating** the TF-IDF classifier's threshold against LLM labels on
a random arXiv sample.

The idea: label the 55k conference papers with the LLM (done in the parent
project), train TF-IDF on those labels, run TF-IDF over all of arXiv, and use a
small LLM-labelled random arXiv sample to set the operating threshold so the
classify-and-count prevalence is unbiased on the arXiv distribution.

## Pipeline (run in order)

| Step | Script | What it does | Output |
|------|--------|--------------|--------|
| 1 | `1_train_classifier.py` | Train TF-IDF+LogReg on the 55k conference LLM-labels (safety vs not). Random + temporal eval. | `data/model/safety_tfidf.pkl`, `roc_curve.png`, `pr_curve.png` |
| 2 | `2_tune_hyperparams.py` | (optional) grid-search TF-IDF/LogReg params. Confirms bigrams + C=10. | stdout |
| 3 | `3_fetch_arxiv.py` | Fetch cs.LG/cs.AI/cs.CL/stat.ML abstracts month-by-month (resumable). | `data/arxiv/papers.csv` |
| 4 | `4_classify_arxiv.py` | Apply TF-IDF to all ~400k arXiv papers. | `data/arxiv/predictions.csv` |
| 5 | `5_build_calibration_sample.py` | Draw 3,000 random arXiv papers to LLM-label (reuses any already labelled). | `data/arxiv/calibration/random_sample.csv`, `random_to_label.csv` |
| —  | `../classify.py` | LLM-label the sample: `python src/classify.py --input .../random_to_label.csv --output .../random_labeled.csv` | `random_labeled.csv` |
| 6 | `6_calibrate_and_validate.py` | Head-to-head: conference-only vs conference+arXiv training (5-fold CV on the 3,000). Sets the prevalence-matched threshold. | stdout, `data/model/arxiv_threshold.json` |
| 7 | `7_plot_trend.py` | Monthly % safety trend at the calibrated threshold. | `data/arxiv/plots/safety_trend.png`, `monthly_trend.csv` |

Steps 3–4 and the step-5 labelling need, respectively, patience (arXiv rate
limits) and `OPENROUTER_API_KEY`.

## Key results

- TF-IDF transfers to arXiv well: **ROC-AUC 0.985** on a held-out arXiv sample.
- Adding arXiv papers to training does **not** help (PR-AUC 0.850–0.852, within
  noise) — the model was fine; only the threshold needed domain calibration.
- Calibrated threshold **0.669** (matches arXiv's true 3.77% safety rate,
  113/3000 labels) → **79% precision / 79% recall**, up from 61% precision at
  the naive conference threshold.
- Per-year arXiv prevalence then matches the independent conference ground
  truth to log-MSE 0.034.
- **Trend: AI-safety share of arXiv ML papers rose 0.4% (2019) → 9.3% (2026)**,
  inflection at end-2022.

The threshold is a single global value; the per-year shape is an *output* of the
classifier on each month's papers, not fitted per year.
