#!/usr/bin/env bash
#
# Manually verify org matches: re-fetch a random sample and print each match's
# surrounding text with a region label (AUTHOR-BLOCK / ABSTRACT-INTRO / ACK),
# so you can tell real affiliations/acknowledgments from citations/mentions.
# Password is prompted hidden and never stored.
#
# Examples:
#   scripts/run_org_verify.sh --n 20 --tier adjacent   # check the OpenAI/Anthropic-type hits
#   scripts/run_org_verify.sh --n 15 --tier only       # check the independent-org hits

set -euo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

VENV="/home/emanuelr/my_env/bin/activate"
[ -f "$VENV" ] && source "$VENV"

if [ -z "${OPENREVIEW_USERNAME:-}" ]; then
    read -rp "OpenReview email: " OPENREVIEW_USERNAME
fi
if [ -z "${OPENREVIEW_PASSWORD:-}" ]; then
    read -rsp "OpenReview password: " OPENREVIEW_PASSWORD
    echo
fi
export OPENREVIEW_USERNAME OPENREVIEW_PASSWORD

exec python3 src/verify_org_context.py "$@"
