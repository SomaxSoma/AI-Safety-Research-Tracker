# Safety-org affiliation analysis

For the conference safety papers, detect which AI-safety organisations are
behind them (author affiliations + funding/program acknowledgments), typed by
legal structure (corporate / PBC / nonprofit / academic / government / funder).

Keyword matching alone over-counts badly — labs like OpenAI / Anthropic /
Hugging Face are *cited* constantly ("we use GPT-4"), not affiliated. So an LLM
second pass classifies each keyword hit as **affiliation / acknowledgment /
mention / absent**, keeping only real associations, and picks each paper's
**primary** org by author weight (e.g. 4 Anthropic authors + 2 MATS mentees →
Anthropic).

## Pipeline

| Step | Script | Online? | What it does | Output |
|------|--------|---------|--------------|--------|
| 1 | `fetch_plaintext.py` | yes (OpenReview login) | download every safety paper's PDF, extract plaintext, discard the PDF | `data/plaintext/*.txt` |
| 2 | `verify_orgs.py` | LLM only (OpenRouter) | keyword-match orgs on the saved text, LLM-verify each, pick primary | `data/org_verified.csv` |
| 3 | `plot.py` | no | combined + 6-type-by-year plots + verified top-orgs | `data/org_plots/*.png` |
| — | `review_csv.py` | no | human-reviewable CSV (title, orgs, per-org verdicts, url) | `data/org_review.csv` |

Wrappers (prompt for creds, hidden): `scripts/run_fetch_plaintext.sh`,
`scripts/run_org_verify_llm.sh`.

Only step 1 needs OpenReview; after it, everything is offline and reproducible
from the saved plaintext. `data/plaintext/` is git-ignored (large + paper full
text) — regenerate it with step 1.

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

- Counts reflect the **primary** affiliation: a MATS-mentored paper authored at
  Anthropic counts as Anthropic. So program counts (MATS, SPAR…) are lower-bound
  — a secondary mentorship credit in a deep acknowledgment on a paper authored
  elsewhere may not be captured (the region scanned is page 1 + the first
  acknowledgments window).
- **ICML 2026 has no PDFs** (papers are pre-conference abstracts) and is
  genuinely unfetchable — it stays in the coverage report as MISSING. Any other
  paper that fails to download is likewise excluded, so denominators are the
  fetchable safety papers. The covered conference-years shown in the share plots
  are computed from the data, so they update automatically as coverage grows.
