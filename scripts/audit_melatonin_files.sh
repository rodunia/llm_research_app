#!/bin/bash
# Audit all 10 melatonin user files with enhanced spec validation

cd /Users/dorotajaguscik/PycharmProjects/llm_research_app

echo "Auditing 10 melatonin files..."
echo "Each file contains one intentional mistake"
echo ""

# Run audit on each melatonin file
for i in {1..10}; do
    echo "Auditing: user_melatonin_$i"
    PYTHONPATH=. python3 analysis/glass_box_audit.py --run-id "user_melatonin_$i" >> /tmp/melatonin_audit.log 2>&1
done

echo ""
echo "Audit complete! Check results:"
echo "  grep '^user_melatonin' results/final_audit_results.csv"
echo ""
echo "To see which mistakes were caught, run:"
echo "  python3 scripts/analyze_melatonin_detections.py"
