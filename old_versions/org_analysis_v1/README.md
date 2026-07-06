# Org analysis v1 (superseded)

The first org-affiliation analysis. Two flaws fixed in the current version
(`src/org_analysis/`):
1. **Two-tier scheme** (safety-only vs safety-adjacent) → replaced by a single
   safety-org class typed by legal structure (corporate / PBC / nonprofit /
   academic / government / funder), OpenAI→PBC from 2026.
2. **Raw keyword counts, no verification** → inflated by citations (Hugging
   Face / OpenAI / Anthropic mentions). Replaced by an LLM pass that keeps only
   affiliations/acknowledgments and picks a primary org.

Files here:
- `org_detect.py` — the online keyword pass (downloaded each PDF, matched orgs).
  Superseded by `fetch_plaintext.py` + `verify_orgs.py` (download once, then
  offline). Its `get_pdf_bytes` helper now lives in `src/org_analysis/pdf_fetch.py`.
- `org_matches.csv` — its raw keyword output (two-tier columns, includes the
  dropped Hugging Face / Meta counts).
- `plot_org_composition.py`, `org_composition_by_year.png`, `top_orgs.png` — the
  old two-tier plots.
- `verify_org_context.py`, `run_org_verify.sh` — a manual PDF-refetch spot-check,
  superseded by `review_csv.py` (reads the saved plaintext, no refetch).
- `test_openreview_auth.py` — one-off check that authenticated OpenReview PDF
  download works.
- `run_org_detect.sh` — wrapper for the old keyword pass.

Current outputs: `data/org_plots/` (org_backed_combined.png, org_backed_by_type.png,
top_orgs_verified.png), `data/org_verified.csv`, `data/org_review.csv`.
