#!/usr/bin/env bash
#
# Download every safety paper's PDF, extract the plaintext to data/plaintext/,
# and discard the PDF. Run with your OpenReview login; afterwards all org
# analysis runs offline from the saved text. Password prompted hidden.
# Resumable (skips ids already saved), so re-running only fetches what's missing.
# OpenReview is pulled via both the v2 and v1 APIs; a per conference-year
# coverage report prints at the end. ~1h for a full first run (~1,740 fetchable
# safety papers; ICML 2026 has no PDFs and stays uncovered).

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

exec python3 src/org_analysis/fetch_plaintext.py "$@"
