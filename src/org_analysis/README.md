# Safety-org affiliation analysis

For the conference safety papers, detect which AI-safety organisations are
behind them (author affiliations + funding/program acknowledgments), typed by
legal structure (corporate / PBC / nonprofit / academic / government / funder).

Keyword matching alone over-counts badly — labs like OpenAI / Anthropic /
Hugging Face are *cited* constantly ("we use GPT-4"), not affiliated. So an LLM
second pass classifies each keyword hit as **affiliation / acknowledgment /
mention / absent**, keeping only real associations. It also picks each paper's
**primary org** (who led the work) and **primary funder** separately, with these
rules:

- A **company** (DeepMind, OpenAI, Anthropic, Google, startups) is primary only
  if it actually leads the work — most/plurality of authors. A lone company
  author among university authors is **University/Independent/other**, not the
  company.
- A **safety program / org** (MATS, SPAR, Apart, safety centres, AISIs) hosts the
  research and is primary even when the authors sit at various universities and
  it appears only in acknowledgments/mentorship (e.g. a MATS paper with an
  Anthropic mentor is *MATS*).
- **Funders** (Open Phil, LTFF…) are never the primary org; they surface as the
  separate **primary funder**.

To let the LLM see the full author list (needed to judge who leads), it gets the
whole front-matter + acknowledgments region, not just keyword windows.

## Pipeline

| Step | Script | Online? | What it does | Output |
|------|--------|---------|--------------|--------|
| 1 | `fetch_plaintext.py` | yes (OpenReview login) | download every safety paper's PDF, extract plaintext, discard the PDF | `data/plaintext/*.txt` |
| 2 | `verify_orgs.py` | LLM only (OpenRouter) | keyword-match orgs on the saved text, LLM-verify each, pick primary org + primary funder | `data/org_verified.csv` |
| 3 | `plot.py` | no | org-backing + by-type plots (by primary org), plus a **research-orgs vs funders** split (a lone-company-author / funder-only paper is *University/Independent/other*), with both tallies saved as CSV | `data/org_plots/*.png`, `orgs.csv`, `funders.csv` |
| — | `review_csv.py` | no | human-reviewable CSV (title, orgs, funders, primary org, primary funder, verdicts, url) | `data/org_review.csv` |

Wrappers (prompt for creds, hidden): `scripts/run_fetch_plaintext.sh`,
`scripts/run_org_verify_llm.sh`.

Only step 1 needs OpenReview; after it, everything is offline and reproducible
from the saved plaintext. `data/plaintext/` is git-ignored (large + paper full
text) — regenerate it with step 1.

**Reproducing step 2:** `verify_orgs.py` reprocesses every safety paper with
plaintext (calling the LLM only for the ~1,100 with a keyword hit) — to
regenerate `org_verified.csv` from scratch, delete it and re-run. The method is
reproducible (output determined by the plaintext, the prompt, and
`ai_safety_orgs.py`), though exact counts wobble by a few papers between runs
since the LLM runs at temperature 1 (matching the classifier). It is concurrent
(`--workers`, default 32) and resumable. (`--reverify` is a cheaper convenience
that re-runs only the papers already having a confirmed org, e.g. after a prompt
tweak, and migrates the rest.)

Shared modules: `pdf_fetch.py` (PDF byte fetch: OpenReview v2+v1 auth / PMLR /
nips), `org_structure.py` (the retained safety-org set + structural typing). The
org keyword list itself is `ai_safety_orgs.py` at the repo root.

`fetch_plaintext.py` fetches OpenReview via **both** APIs — the v2 client
(ICLR 2024+, NeurIPS 2023+, ICML 2024+) with a **v1 fallback** (ICLR ≤2023,
NeurIPS 2021–2022, whose legacy `Blind_Submission` ids the v2 client cannot
resolve). It is resumable (skips ids already saved), so re-running only fetches
what is still missing, and prints a per conference-year **coverage report** at
the end so any remaining gap is explicit rather than silently dropped.

## Notes

- The **research-orgs plot counts by primary org** (each paper once, under the
  org that led it); the **funders plot counts by association** (a paper can
  acknowledge several). Program credits (MATS, SPAR…) are still a lower bound —
  a mentorship credit in a deep acknowledgment beyond the scanned region (page 1
  + first acknowledgments window) may be missed.
- **ICML 2026 has no PDFs** (papers are pre-conference abstracts) and is
  genuinely unfetchable — it stays in the coverage report as MISSING. Any other
  paper that fails to download is likewise excluded, so denominators are the
  fetchable safety papers. The covered conference-years shown in the share plots
  are computed from the data, so they update automatically as coverage grows.
