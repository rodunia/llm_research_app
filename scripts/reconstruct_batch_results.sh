#!/bin/bash
# Reconstruct complete batch audit results by re-running all 10 files quickly

cd /Users/dorotajaguscik/PycharmProjects/llm_research_app

OUTPUT_CSV="$1"
RUN_PREFIX="$2"

if [ -z "$OUTPUT_CSV" ] || [ -z "$RUN_PREFIX" ]; then
    echo "Usage: $0 <output_csv> <run_prefix>"
    echo "Example: $0 results/pilot_baseline_corecoin_complete.csv user_corecoin"
    exit 1
fi

echo "Reconstructing batch results for $RUN_PREFIX..."
echo "Filename,Status,Violated_Rule,Extracted_Claim,Confidence_Score" > "$OUTPUT_CSV"

for i in {1..10}; do
    RUN_ID="${RUN_PREFIX}_$i"
    echo "Processing $RUN_ID..."

    # Run audit
    PYTHONPATH=. python3 analysis/glass_box_audit.py --run-id "$RUN_ID" > /dev/null 2>&1

    # Append results (skip header)
    if [ -f results/final_audit_results.csv ]; then
        tail -n +2 results/final_audit_results.csv >> "$OUTPUT_CSV"
    fi
done

echo "Done! Complete results saved to $OUTPUT_CSV"
wc -l "$OUTPUT_CSV"
