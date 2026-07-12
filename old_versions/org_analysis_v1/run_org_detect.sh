#!/usr/bin/env bash
#
# Detect AI-safety-organisation affiliations in conference papers.
# Prompts for your OpenReview credentials (password hidden), then runs the
# detector. The password is never echoed, stored, or written anywhere.
#
# Run it from anywhere; it cd's to the repo automatically.
#
# Examples:
#   scripts/run_org_detect.sh --safety-only               # ~2,300 safety papers (~2h)
#   scripts/run_org_detect.sh                               # all ~55k papers (~40h)
#   scripts/run_org_detect.sh --conference iclr --year 2026
#
# The job is RESUMABLE: appends to data/org_matches.csv and skips ids already
# done, so you can Ctrl-C and re-run any time, or it survives a shutdown.
# For the long full run, keep it alive across a closed terminal with:
#   nohup scripts/run_org_detect.sh > org_detect.log 2>&1 &
# (nohup can't prompt, so set OPENREVIEW_USERNAME/PASSWORD in the env first,
#  or just re-run in the foreground — resume makes that painless.)

set -euo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"   # repo root

VENV="/home/emanuelr/my_env/bin/activate"
if [ -f "$VENV" ]; then
    # shellcheck disable=SC1090
    source "$VENV"
fi

if [ -z "${OPENREVIEW_USERNAME:-}" ]; then
    read -rp "OpenReview email: " OPENREVIEW_USERNAME
fi
if [ -z "${OPENREVIEW_PASSWORD:-}" ]; then
    read -rsp "OpenReview password: " OPENREVIEW_PASSWORD
    echo
fi
export OPENREVIEW_USERNAME OPENREVIEW_PASSWORD

exec python3 src/org_detect.py "$@"
