# AI Safety Research Tracker — Website

Static site implementing the "AI Safety Research Tracker v2" design. No build step, no dependencies — plain HTML/CSS/JS.

Data companion repo: https://github.com/SomaxSoma/AI-Safety-Research-Tracker

## Run

Serve the folder over HTTP (any static server works):

```bash
python -m http.server 8642
# open http://localhost:8642/
```

## Structure

```
index.html       # page skeleton (masthead, hero, tabs, panel, footer, feedback FAB)
css/styles.css   # all styling (dark mono theme, IBM Plex Mono)
js/data.js       # datasets — aggregates cross-checked against the tracker repo;
                 # the arXiv trend chart uses the real data/arxiv/monthly_trend.csv series
js/app.js        # rendering + interactions (tabs, charts, drilldown, explorer, feedback)
data/papers.json # all 2,328 safety papers [title, venue, year, subdomain, score, url]
                 # generated from the repo's per-conference filtered/safety.csv files
```

## Features

- **Sticky glass navigation** — tabs sit directly under the masthead and stay pinned while scrolling, with a subtle frosted-glass effect that deepens with scroll (near-transparent at rest → glass past 20px → higher opacity past 150px). OVERVIEW (the hero: animated 4.2% share, per-year bars) is the default view, and the masthead title links home.
- **10 views** — Overview, Conferences (POOLED / BY VENUE faces), Subareas, Detailed Classes (ICLR 2026 / BY YEAR drilldown with ↑/↓ keys / TRENDS composition-over-time lines), Scores, Major Classes, Who Publishes (ALL ORGS / PRIMARY / FUNDERS / BY YEAR — 55 verified research orgs + 7 funders), Papers explorer (click a row for the classifier's verbatim reasoning and per-axis scores), arXiv Trend (real 90-month series with hover crosshair; a calibrated TF-IDF classifier, ~72% precision / 74% recall — a rough experimental trend), and Implementation (the DeepSeek V4 Flash pipeline that reads each paper's title + abstract).
- **Deep links** — every view has a URL hash (`#arxiv`, `#method`, …); browser back/forward works.
- **Custom tooltips** — styled hover tooltips on all bars; the arXiv chart shows a crosshair with rolling %, monthly %, and volume.
- **Who publishes** (`#orgs`) — verified safety-org affiliations from the repo's full-text org analysis (`data/org_verified.csv`): top orgs by paper count plus a by-legal-structure face; includes funders (Open Philanthropy, LTFF) that co-authorship analyses can't see.
- **Paper explorer** (`#papers`) — search and filter all 2,328 safety papers by title, venue, year, and subdomain; every row links to the paper page.
- **Glossary tooltips** — hovering any subdomain/subarea bar or chip shows its definition from the classification rubric (`src/prompt.txt`).
- **Notable papers** — progressive-disclosure list on chart views; each title links to its OpenReview page.
- **Feedback** — floating action button opens a modal (feature/bug/data types, severity for bugs, character counters); submitting opens a prefilled GitHub issue on the tracker repo.
- **GitHub badge** — live star count in the masthead (GitHub API), linking to the repo.
- **Responsive** — single-column layout, scrollable tabs, and scaled type below 980px/760px/480px; no horizontal scroll on phones.
- **A11y & meta** — keyboard-navigable tabs (arrow keys, Enter/Space, focus rings), favicon, Open Graph/Twitter card tags, data-freshness stamp in the footer.

## Aggregate plots (research pipeline)

Cross-conference summaries of the classifier output, regenerated from
`data/{conf}/{year}/results.csv`. Written to `data/aggregate_plots/`:

- `safety_share_by_year.png` / `safety_share_by_conf.png` — AI-safety share of
  accepted papers per year, pooled and split by venue.
- `safety_areas_composition.png` — fine-subdomain composition over time (lines
  sum to 100% per year).
- `safety_subdomains_all_years.png` / `safety_subdomains_per_year.png` —
  subdomain breakdown, pooled and as per-year small multiples.
- `org_only/` — the same five views restricted to the safety papers with an
  LLM-verified safety-org affiliation (`data/org_verified.csv`, ~600 papers).

```bash
python src/aggregate_plots.py        # all-safety views
python src/aggregate_plots_orgs.py   # org-affiliated views
```
