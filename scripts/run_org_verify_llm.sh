#!/usr/bin/env bash
#
# LLM second pass: for every safety paper with saved plaintext, keyword-match the
# retained safety orgs, then have the LLM confirm affiliation/acknowledgment vs
# mention and pick each paper's primary org. Fully OFFLINE from the plaintext —
# only needs an OpenRouter key (no OpenReview login). Resumable.
#
# Run fetch_plaintext first (scripts/run_fetch_plaintext.sh). Then:
#   OPENROUTER_API_KEY=sk-or-... scripts/run_org_verify_llm.sh

set -euo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

VENV="/home/emanuelr/my_env/bin/activate"
[ -f "$VENV" ] && source "$VENV"

if [ -z "${OPENROUTER_API_KEY:-}" ]; then
    read -rsp "OpenRouter API key: " OPENROUTER_API_KEY; echo
fi
export OPENROUTER_API_KEY

exec python3 src/org_analysis/verify_orgs.py "$@"
