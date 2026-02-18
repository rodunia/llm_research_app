#!/bin/bash
# Audit all 10 CoreCoin files sequentially

export PYTHONPATH=.

echo "Auditing 10 CoreCoin files..."

for i in {1..10}; do
    echo ""
    echo "=== Auditing user_corecoin_$i ==="
    python3 analysis/glass_box_audit.py --run-id user_corecoin_$i --clean 2>&1 | grep -E "(violations=|PASS|FAIL)"
done

echo ""
echo "Done! Results saved to results/final_audit_results.csv"
