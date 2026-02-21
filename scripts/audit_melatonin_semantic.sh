#!/bin/bash
# Audit Melatonin pilot study WITH semantic pre-filtering

cd /Users/dorotajaguscik/PycharmProjects/llm_research_app

echo "Auditing 10 Melatonin files WITH semantic pre-filtering..."
echo ""

for i in {1..10}; do
    echo "=== Auditing user_melatonin_$i (WITH SEMANTIC FILTER) ==="
    python3 analysis/glass_box_audit.py --run-id user_melatonin_$i --use-semantic-filter 2>&1 | grep -E "(violations|PASS|FAIL|supplement_melatonin)"
    echo ""
done

echo "Done! Results saved to results/final_audit_results.csv"
