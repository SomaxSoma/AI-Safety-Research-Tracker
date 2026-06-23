#!/usr/bin/env bash
# Fetch all supported conference-year combinations.
# Logs each fetch to /tmp/fetch_<conf>_<year>.log and prints a summary.

set -uo pipefail

cd "$(dirname "$0")/.."

COMBOS=(
  "iclr 2020"     "iclr 2021"     "iclr 2022"    "iclr 2023"
  "iclr 2024"     "iclr 2025"     "iclr 2026"
  "icml 2020"     "icml 2021"     "icml 2022"
  "icml 2023"     "icml 2024"     "icml 2025"
  "neurips 2020"  "neurips 2021"  "neurips 2022"
  "neurips 2023"  "neurips 2024"  "neurips 2025"
)

mkdir -p /tmp/fetch_logs
results=()
total_papers=0

for combo in "${COMBOS[@]}"; do
  read -r conf year <<< "$combo"
  log=/tmp/fetch_logs/${conf}_${year}.log
  echo "==> Fetching $conf $year (log: $log)"

  start=$(date +%s)
  if python src/fetch.py "$conf" "$year" > "$log" 2>&1; then
    elapsed=$(( $(date +%s) - start ))
    n=$(tail -3 "$log" | grep -oP 'Saved \K\d+' | head -1)
    n=${n:-?}
    results+=("OK  $conf $year  $n papers  ${elapsed}s")
    total_papers=$(( total_papers + ${n:-0} ))
  else
    elapsed=$(( $(date +%s) - start ))
    results+=("FAIL $conf $year  (${elapsed}s — see $log)")
  fi
done

echo
echo "============================================================"
echo "SUMMARY"
echo "============================================================"
for r in "${results[@]}"; do echo "  $r"; done
echo
echo "Total papers fetched: $total_papers"
