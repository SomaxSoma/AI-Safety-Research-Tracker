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

- **Sticky glass navigation** — tabs sit directly under the masthead and stay pinned while scrolling, with a subtle frosted-glass effect that deepens with scroll (near-transparent at rest → glass past 20px → higher opacity past 150px). OVERVIEW (the hero: animated 4.2% share, per-year bars) is the default view, METHOD is the second tab, and the masthead title links home.
- **11 views** — Overview, Method (incl. the independent-replication citation), Conferences (POOLED / BY VENUE faces), arXiv Trend (real 90-month series with hover crosshair), Subareas, Detailed Classes (ICLR 2026 / BY YEAR drilldown with ↑/↓ keys / TRENDS composition-over-time lines), Scores, Major Classes, Who Publishes (TOP ORGS / BY TYPE / BY YEAR org-backed share), Papers explorer (click a row for the classifier's verbatim reasoning and per-axis scores), Classifier metrics.
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
