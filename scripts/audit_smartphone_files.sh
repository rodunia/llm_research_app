#!/bin/bash
# Audit all 10 smartphone user files with enhanced spec validation

cd /Users/dorotajaguscik/PycharmProjects/llm_research_app

echo "Auditing 10 smartphone files (s1.txt - s10.txt)..."
echo "Each file contains one intentional mistake"
echo ""

# Run audit on each smartphone file
for i in {1..10}; do
    echo "Auditing: user_smartphone_$i (outputs/s$i.txt)"
    PYTHONPATH=. python3 analysis/glass_box_audit.py --run-id "user_smartphone_$i" >> /tmp/smartphone_audit.log 2>&1
done

echo ""
echo "Audit complete! Check results:"
echo "  grep '^user_smartphone' results/final_audit_results.csv"
echo ""
echo "To see which mistakes were caught, run:"
echo "  python3 scripts/analyze_smartphone_detections.py"
