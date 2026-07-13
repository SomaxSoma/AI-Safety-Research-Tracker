#!/usr/bin/env bash
#
# Match ICML 2026 accepted papers to OpenReview by title and write their
# OpenReview pdf_url into data/icml/2026/papers.csv, so fetch_plaintext can then
# download the PDFs. Run ONCE with your OpenReview login; password prompted
# hidden. Idempotent. Afterwards run scripts/run_fetch_plaintext.sh.

set -euo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

VENV="/home/emanuelr/my_env/bin/activate"
[ -f "$VENV" ] && source "$VENV"

if [ -z "${OPENREVIEW_USERNAME:-}" ]; then
    read -rp "OpenReview email: " OPENREVIEW_USERNAME
fi
if [ -z "${OPENREVIEW_PASSWORD:-}" ]; then
    read -rsp "OpenReview password: " OPENREVIEW_PASSWORD; echo
fi
export OPENREVIEW_USERNAME OPENREVIEW_PASSWORD

exec python3 src/org_analysis/backfill_icml2026.py "$@"
