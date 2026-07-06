# Superseded versions

Kept for provenance; **not part of the current pipeline.**

| Item | What it was | Why it's here / what replaced it |
|------|-------------|----------------------------------|
| `tune_threshold.py` | Tuned the TF-IDF threshold on the **conference** data to a yearly log-prevalence objective (→ 0.555). | The arXiv trend needs an **arXiv-domain** threshold. That's now set by `src/arxiv_trend/6_calibrate_and_validate.py` against LLM labels on random arXiv papers (→ 0.669). |
| `calibrate_arxiv_analyze.py` | First calibration pass: a 698-paper sample (400 random + 298 predicted-positive), precision/recall/confusion vs DeepSeek. | Superseded by the 3,000-random-paper design in step 6, which pins the prevalence far more tightly (113 positives vs 15) and also runs the domain-adaptation A/B test. |
| `data_698_calibration/sample.csv`, `sample_deepseek.csv` | The 698-paper first sample and its DeepSeek labels. | Replaced by `data/arxiv/calibration/random_sample.csv` + `random_labeled.csv` (3,000). |
| `data_698_calibration/random_to_label.csv` | Transient "to-label" list from step 5. | Regenerable by re-running step 5. |
| `data_698_calibration/conference_threshold_tuning.png` | Diagnostic plot from `tune_threshold.py` (conference log-prevalence fit). | Conference-domain artifact, superseded by the arXiv calibration. |

Also dropped earlier this session (not kept): the **adjusted-count correction**
approach (`apply_calibration.py`, `safety_trend_calibrated.png`) — replaced by
directly re-tuning the threshold, which removes the borderline false positives
rather than scaling counts.
