#!/bin/bash
# Audit only user-uploaded files

cd /Users/dorotajaguscik/PycharmProjects/llm_research_app

echo "Auditing 30 user-uploaded files..."
echo "Files: user_corecoin_* (10), user_smartphone_* (10), user_melatonin_* (10)"
echo ""

# Run audit on each user file
for run_id in $(grep "^user_" results/experiments.csv | cut -d',' -f1); do
    echo "Auditing: $run_id"
    PYTHONPATH=. python3 analysis/glass_box_audit.py --run-id "$run_id" >> /tmp/user_files_audit.log 2>&1
done

echo ""
echo "Audit complete! Check results:"
echo "  grep '^user_' results/final_audit_results.csv"
