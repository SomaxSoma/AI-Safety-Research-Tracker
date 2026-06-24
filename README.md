# AI Safety Research Tracker — ICLR / ICML / NeurIPS

Classifies accepted papers from major ML conferences into four categories (Ethics & Fairness, Truthfulness & Reliability, General Capabilities, AI Safety) using DeepSeek V4 Flash with reasoning, and breaks the safety papers into 17 subdomains following a frontier-AI-safety-focused taxonomy.

## Headline result

**2,328 AI safety papers out of 55,794 (4.2%) across ICLR/ICML/NeurIPS 2019–2026.**

Safety-paper share has grown ~28× since 2019, with a sharp inflection in 2024 after frontier LLM deployment:

| Year | Papers | Safety | Share |
|---|---|---|---|
| 2019 | 2,701 | 9 | 0.3% |
| 2020 | 3,669 | 26 | 0.7% |
| 2021 | 4,674 | 31 | 0.7% |
| 2022 | 4,998 | 48 | 1.0% |
| 2023 | 6,619 | 101 | 1.5% |
| 2024 | 8,905 | 370 | 4.2% |
| 2025 | 12,249 | 744 | 6.1% |
| 2026 | 11,979 | 999 | 8.3% |

Highest single-conference share so far: **ICML 2026 at 8.9%**.

### Example: ICLR 2026

![AI Safety at ICLR 2026](data/iclr/2026/plots/overview.png)

![Score Distribution](data/iclr/2026/plots/score_distribution.png)

## Pipeline

```bash
# 1. Fetch accepted papers
python src/fetch.py iclr 2026
python src/fetch.py icml 2026          # uses icml.cc/virtual scraper
python src/fetch.py neurips 2020       # uses papers.nips.cc scraper

# 2. Classify with the LLM (needs OPENROUTER_API_KEY env var)
python src/classify.py iclr 2026

# 3. Generate plots and filtered CSVs
python src/visualize.py iclr 2026
```

Each step writes under `data/{conference}/{year}/`:
```
data/iclr/2026/
├── papers.csv              # output of fetch
├── results.csv             # output of classify
├── plots/
│   ├── overview.png
│   ├── major_classes.png
│   ├── safety_subareas.png
│   ├── detailed_classes.png
│   └── score_distribution.png
└── filtered/
    ├── safety.csv          # safety papers (title, subarea, class, score)
    ├── ethics_fairness.csv
    └── truthfulness_reliability.csv
```

Classification rubric lives in [src/prompt.txt](src/prompt.txt). Methodology iterations are archived in `runs/`.

## Coverage

23 conference-years across four data sources:

| Conference | Years | Source |
|---|---|---|
| ICLR | 2019–2023 | OpenReview v1 |
| ICLR | 2024–2026 | OpenReview v2 |
| ICML | 2019–2022 | PMLR scraper |
| ICML | 2023–2025 | OpenReview v2 |
| ICML | 2026 | icml.cc virtual scraper (no OpenReview/PMLR yet) |
| NeurIPS | 2019–2020 | papers.nips.cc scraper |
| NeurIPS | 2021–2022 | OpenReview v1 |
| NeurIPS | 2023–2025 | OpenReview v2 |

All sources produce the same row schema: `id, conference, year, title, authors, author_ids, abstract, keywords, primary_area, venue, tldr, url, pdf_url`. Some fields are empty on non-OpenReview sources (notably `author_ids`, `keywords`, `primary_area`, `tldr`).

## Concurrency safety

The classifier (`src/classify.py`) takes an exclusive file lock on its output CSV so that two concurrent runs targeting the same conference cannot interleave writes and corrupt the file. Resume support also means re-running `classify.py` on a partially-finished output skips papers already classified.

## Repo layout

```
.
├── src/
│   ├── fetch.py            # multi-conference paper fetcher (4 sources)
│   ├── classify.py         # async parallel LLM classifier with resume
│   ├── visualize.py        # plot + filtered-CSV generator
│   └── prompt.txt          # classification rubric
├── data/
│   ├── iclr/{2019..2026}/
│   ├── icml/{2019..2026}/
│   └── neurips/{2019..2025}/
├── scripts/
│   └── fetch_all.sh        # batch-fetch helper
├── runs/                   # archived methodology iterations
│   ├── v1/                 #   Gemma 4 31B + original prompt
│   ├── v2/                 #   Gemma 4 31B + refined prompt
│   └── v3_sample/          #   DeepSeek V4 Flash + reasoning, 1/4 sample
└── README.md
```
