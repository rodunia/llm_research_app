#!/bin/bash
# Rerun all 30 pilot audits and save individual CSVs

source .venv/bin/activate

mkdir -p results/pilot_individual_2026

echo "=========================================="
echo "Re-running Pilot Study (30 files)"
echo "=========================================="
echo ""

# CoreCoin (10 files)
echo "--- CoreCoin (10 files) ---"
for i in 1 2 3 4 5 6 7 8 9 10; do
    echo "Auditing user_corecoin_$i..."
    python3 analysis/glass_box_audit.py --run-id user_corecoin_$i --clean
    if [ -f results/final_audit_results.csv ]; then
        cp results/final_audit_results.csv results/pilot_individual_2026/corecoin_$i.csv
        echo "✓ Saved corecoin_$i.csv ($(wc -l < results/final_audit_results.csv) rows)"
    fi
    echo ""
done

# Smartphone (10 files)
echo "--- Smartphone (10 files) ---"
for i in 1 2 3 4 5 6 7 8 9 10; do
    echo "Auditing user_smartphone_$i..."
    python3 analysis/glass_box_audit.py --run-id user_smartphone_$i --clean
    if [ -f results/final_audit_results.csv ]; then
        cp results/final_audit_results.csv results/pilot_individual_2026/smartphone_$i.csv
        echo "✓ Saved smartphone_$i.csv ($(wc -l < results/final_audit_results.csv) rows)"
    fi
    echo ""
done

# Melatonin (10 files)
echo "--- Melatonin (10 files) ---"
for i in 1 2 3 4 5 6 7 8 9 10; do
    echo "Auditing user_melatonin_$i..."
    python3 analysis/glass_box_audit.py --run-id user_melatonin_$i --clean
    if [ -f results/final_audit_results.csv ]; then
        cp results/final_audit_results.csv results/pilot_individual_2026/melatonin_$i.csv
        echo "✓ Saved melatonin_$i.csv ($(wc -l < results/final_audit_results.csv) rows)"
    fi
    echo ""
done

echo "=========================================="
echo "All 30 audits complete!"
echo "Results saved to: results/pilot_individual_2026/"
echo "=========================================="
