#!/usr/bin/env bash
#
# Download every safety paper's PDF, extract the plaintext to data/plaintext/,
# and discard the PDF. Run ONCE with your OpenReview login; afterwards all org
# analysis runs offline from the saved text. Password prompted hidden.
# Resumable (skips ids already saved). ~1h for all ~1,700 fetchable safety papers.

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
