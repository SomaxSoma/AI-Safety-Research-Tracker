# ICLR 2026 — AI Safety Paper Analysis

Fetches every ICLR 2026 submission from OpenReview, uses an LLM to classify which ones are AI safety research, and breaks the results down by subdomain.

## Pipeline

1. [fetch_papers.py](fetch_papers.py) — pull all ICLR 2026 submissions from the OpenReview API → `iclr2026_papers.csv`
2. [classify.py](classify.py) — classify each paper as safety / not-safety and assign a subdomain → `safety_results.csv`
3. [analyze.py](analyze.py) — aggregate counts and render the chart below
4. [download_pdfs.py](download_pdfs.py) — download PDFs for the safety papers, organized by subdomain

## Result

![AI Safety at ICLR 2026](ai_safety_iclr2026.png)
