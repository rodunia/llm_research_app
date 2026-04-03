#!/bin/bash
# Pilot Study Setup - Complete Isolation from Main Experiment
# This script creates a separate pilot workspace that doesn't touch results/experiments.csv

set -e  # Exit on error

echo "=========================================="
echo "PILOT STUDY SETUP - ISOLATION MODE"
echo "=========================================="
echo ""

# 1. Create pilot workspace
echo "1. Creating pilot workspace..."
mkdir -p pilot/outputs/prompts
mkdir -p pilot/products
mkdir -p pilot/templates
mkdir -p pilot/results
echo "   ✓ Created pilot/ directory structure"
echo ""

# 2. Symlink dependencies (read-only)
echo "2. Symlinking dependencies..."
ln -sf ../products/*.yaml pilot/products/ 2>/dev/null || true
for yaml in products/*.yaml; do
    ln -sf ../$yaml pilot/$yaml
done
for template in templates/*.j2; do
    ln -sf ../$template pilot/$template
done
ln -sf ../.env pilot/.env
echo "   ✓ Symlinked products, templates, .env"
echo ""

# 3. Create pilot CSV (30 runs, stratified by engine)
echo "3. Creating pilot_experiments.csv (30 runs, 10 per engine)..."
python3 << 'PYTHON_SCRIPT'
import pandas as pd

# Load main matrix
df = pd.read_csv('results/experiments.csv')

print(f"   Main matrix: {len(df)} runs, {len(df[df['status']=='pending'])} pending")

# Sample 10 runs per engine (stratified, seed 42)
pilot = df.groupby('engine', group_keys=False).apply(
    lambda x: x.sample(min(10, len(x)), random_state=42)
).copy()

print(f"   Pilot sample: {len(pilot)} runs")
print(f"   Breakdown by engine:")
for engine, count in pilot.groupby('engine').size().items():
    print(f"      {engine}: {count} runs")

# Save to pilot directory
pilot.to_csv('pilot/experiments.csv', index=False)
print(f"   ✓ Saved to pilot/experiments.csv")

# Show sample run_ids
print(f"\n   Sample run_ids (first 3):")
for i, run_id in enumerate(pilot['run_id'].head(3)):
    print(f"      {i+1}. {run_id}")
PYTHON_SCRIPT
echo ""

# 4. Verify main matrix untouched
echo "4. Verifying main matrix isolation..."
python3 << 'PYTHON_VERIFY'
import pandas as pd
main_df = pd.read_csv('results/experiments.csv')
pending = len(main_df[main_df['status'] == 'pending'])
if pending == 1620:
    print(f"   ✓ Main experiments.csv: {pending}/1620 pending (UNTOUCHED)")
else:
    print(f"   ✗ WARNING: Main matrix modified! Expected 1620 pending, got {pending}")
    exit(1)
PYTHON_VERIFY
echo ""

# 5. Instructions
echo "=========================================="
echo "PILOT SETUP COMPLETE ✓"
echo "=========================================="
echo ""
echo "📁 Workspace created:"
echo "   pilot/experiments.csv       (30 runs)"
echo "   pilot/outputs/              (LLM outputs will go here)"
echo "   pilot/results/              (audit results will go here)"
echo ""
echo "🚀 To run pilot:"
echo ""
echo "   # Step 1: Generate marketing materials (Stage 1)"
echo "   cd pilot"
echo "   PYTHONPATH=.. python ../runner/run_job.py batch --csv-path experiments.csv"
echo ""
echo "   # Step 2: Run glass box audit (Stage 2)"
echo "   PYTHONPATH=.. python ../analysis/glass_box_audit.py --limit 30"
echo ""
echo "   # Step 3: Verify results"
echo "   python -c \"import pandas as pd; df=pd.read_csv('experiments.csv'); print(f'Completed: {len(df[df.status==\"completed\"])}/30')\""
echo "   python -c \"import pandas as pd; df=pd.read_csv('results/final_audit_results.csv'); print(f'Audited: {len(df.run_id.unique())} runs')\""
echo ""
echo "🧹 After pilot validation:"
echo "   cd .. && rm -rf pilot/"
echo ""
echo "✅ GUARANTEE: Main results/experiments.csv stays 1,620 pending"
echo "=========================================="
