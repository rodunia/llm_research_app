#!/bin/bash
# Audit CoreCoin files and save each to individual CSV

echo "Auditing 10 CoreCoin files sequentially..."

for i in {1..10}; do
  echo ""
  echo "=== Auditing user_corecoin_$i ==="
  PYTHONPATH=. python3 analysis/glass_box_audit.py --run-id user_corecoin_$i --clean 2>&1 | tail -5

  # Save this run's results to a separate file
  if [ -f results/final_audit_results.csv ]; then
    cp results/final_audit_results.csv results/corecoin_${i}_audit.csv
    echo "  Saved to results/corecoin_${i}_audit.csv"
  fi
done

echo ""
echo "=== Merging all CoreCoin results ==="

# Merge all results (skip header for files after the first)
head -1 results/corecoin_1_audit.csv > results/corecoin_all_audit.csv
for i in {1..10}; do
  tail -n +2 results/corecoin_${i}_audit.csv >> results/corecoin_all_audit.csv
done

echo "Done! All results saved to results/corecoin_all_audit.csv"
wc -l results/corecoin_all_audit.csv
