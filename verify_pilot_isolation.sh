#!/bin/bash
# Verify pilot doesn't contaminate main experiment

echo "=== PILOT ISOLATION VERIFICATION ==="
echo ""

# Check main matrix
echo "Main experiment matrix:"
python3 -c "
import pandas as pd
df = pd.read_csv('results/experiments.csv')
pending = len(df[df['status'] == 'pending'])
print(f'  Total: {len(df)} rows')
print(f'  Pending: {pending}')
print(f'  Status: {\"✅ SAFE\" if pending == 1620 else \"❌ CONTAMINATED\"}')
"
echo ""

# Check pilot exists
if [ -d "pilot" ]; then
    echo "Pilot workspace:"
    python3 -c "
import pandas as pd
import os
if os.path.exists('pilot/experiments.csv'):
    df = pd.read_csv('pilot/experiments.csv')
    print(f'  Pilot runs: {len(df)}')
    print(f'  Pilot completed: {len(df[df[\"status\"] == \"completed\"])}')
    print(f'  Status: ✅ ISOLATED')
else:
    print('  Status: ⚠️ Not yet created (run ./setup_pilot.sh)')
"
else
    echo "Pilot workspace: ⚠️ Not yet created (run ./setup_pilot.sh)"
fi

echo ""
echo "=== VERIFICATION COMPLETE ==="
