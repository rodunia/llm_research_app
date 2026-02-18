#!/bin/bash
# Collect all melatonin audit results into one CSV

export PYTHONPATH=.

# Create header
echo "Filename,Status,Violated_Rule,Extracted_Claim,Confidence_Score" > /tmp/melatonin_all_violations.csv

# Audit each file and append results
for i in {1..10}; do
    echo "Auditing user_melatonin_$i..."
    python3 analysis/glass_box_audit.py --run-id user_melatonin_$i 2>&1 | grep -E "(violations|ERROR)"

    # Append results (skip header)
    tail -n +2 results/final_audit_results.csv >> /tmp/melatonin_all_violations.csv
done

echo ""
echo "=== COMPLETE ==="
echo "Total violations found:"
wc -l /tmp/melatonin_all_violations.csv

echo ""
echo "Violations per file:"
tail -n +2 /tmp/melatonin_all_violations.csv | cut -d',' -f1 | sort | uniq -c

# Copy to results directory
cp /tmp/melatonin_all_violations.csv results/melatonin_pilot_audit_results.csv
echo ""
echo "Results saved to results/melatonin_pilot_audit_results.csv"
