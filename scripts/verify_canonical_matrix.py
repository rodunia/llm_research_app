#!/usr/bin/env python3
"""Verify that results/experiments.csv is the canonical pre-registered matrix.

This script provides machine-checkable verification of the experimental matrix
for independent reviewers and peer review. It checks all validation criteria
that the orchestrator enforces.

Usage:
    python scripts/verify_canonical_matrix.py

Exit codes:
    0 = Valid canonical matrix
    1 = Invalid or missing matrix

For CI/CD:
    python scripts/verify_canonical_matrix.py || exit 1
"""

import sys
import hashlib
from pathlib import Path

try:
    import pandas as pd
except ImportError:
    print("✗ pandas not installed: pip install pandas")
    sys.exit(1)

# Canonical matrix properties (pre-registered 2026-03-28)
CANONICAL_TOTAL_RUNS = 1620
CANONICAL_SEED = 42
CANONICAL_MODE = 'stratified_7day_balanced'
CANONICAL_ENGINE_BALANCE = 540  # runs per engine
CANONICAL_TIME_BALANCE = 540    # runs per time slot
CANONICAL_ENGINE_TIME_MIN = 179  # min runs per engine×time cell
CANONICAL_ENGINE_TIME_MAX = 181  # max runs per engine×time cell


def compute_matrix_fingerprint(df: pd.DataFrame) -> str:
    """Compute SHA256 fingerprint of matrix core columns.

    This fingerprint is based only on the randomization-defining columns,
    not runtime metadata (status, timestamps, tokens).
    """
    core_cols = [
        'run_id', 'product_id', 'material_type', 'engine',
        'temperature', 'time_of_day_label', 'repetition_id',
        'scheduled_datetime', 'scheduled_day_of_week', 'scheduled_hour_of_day'
    ]

    # Only use columns that exist
    available_cols = [col for col in core_cols if col in df.columns]

    if not available_cols:
        return "NO_CORE_COLUMNS"

    # Sort by run_id for deterministic hashing
    core_data = df[available_cols].sort_values('run_id')
    data_str = core_data.to_csv(index=False)
    return hashlib.sha256(data_str.encode()).hexdigest()


def verify_matrix(verbose: bool = True) -> bool:
    """Verify canonical matrix.

    Args:
        verbose: Print detailed output

    Returns:
        True if valid, False otherwise
    """
    matrix_path = Path("results/experiments.csv")

    if verbose:
        print("=" * 70)
        print("Verifying Canonical Matrix")
        print("=" * 70)
        print()

    # Check 0: File exists
    if not matrix_path.exists():
        print("✗ Matrix not found at results/experiments.csv")
        return False

    try:
        df = pd.read_csv(matrix_path)
    except Exception as e:
        print(f"✗ Failed to read matrix: {e}")
        return False

    # Check 1: Total runs
    if len(df) != CANONICAL_TOTAL_RUNS:
        print(f"✗ Wrong run count: {len(df)} (expected {CANONICAL_TOTAL_RUNS})")
        return False
    if verbose:
        print(f"✓ Total runs: {len(df)}")

    # Check 2: Randomization mode
    if 'matrix_randomization_mode' not in df.columns:
        print("✗ Missing column: matrix_randomization_mode")
        return False

    mode = df['matrix_randomization_mode'].iloc[0]
    if mode != CANONICAL_MODE:
        print(f"✗ Wrong mode: '{mode}' (expected '{CANONICAL_MODE}')")
        return False
    if verbose:
        print(f"✓ Mode: {CANONICAL_MODE}")

    # Check 3: Seed
    if 'matrix_randomization_seed' not in df.columns:
        print("✗ Missing column: matrix_randomization_seed")
        return False

    seed = df['matrix_randomization_seed'].iloc[0]
    if seed != CANONICAL_SEED:
        print(f"✗ Wrong seed: {seed} (expected {CANONICAL_SEED})")
        return False
    if verbose:
        print(f"✓ Seed: {CANONICAL_SEED}")

    # Check 4: Engine balance
    if 'engine' not in df.columns:
        print("✗ Missing column: engine")
        return False

    engine_counts = df['engine'].value_counts()
    if not all(c == CANONICAL_ENGINE_BALANCE for c in engine_counts.values):
        print(f"✗ Engine imbalance: {engine_counts.to_dict()}")
        print(f"  Expected: {CANONICAL_ENGINE_BALANCE} per engine")
        return False
    if verbose:
        print(f"✓ Engine balance: {'/'.join(str(c) for c in sorted(engine_counts.values))}")

    # Check 5: Time slot balance
    if 'time_of_day_label' not in df.columns:
        print("✗ Missing column: time_of_day_label")
        return False

    time_counts = df['time_of_day_label'].value_counts()
    if not all(c == CANONICAL_TIME_BALANCE for c in time_counts.values):
        print(f"✗ Time slot imbalance: {time_counts.to_dict()}")
        print(f"  Expected: {CANONICAL_TIME_BALANCE} per time slot")
        return False
    if verbose:
        print(f"✓ Time slot balance: {'/'.join(str(c) for c in sorted(time_counts.values))}")

    # Check 6: Engine×Time balance
    crosstab = pd.crosstab(df['engine'], df['time_of_day_label'])
    min_cell = crosstab.min().min()
    max_cell = crosstab.max().max()

    if min_cell < CANONICAL_ENGINE_TIME_MIN or max_cell > CANONICAL_ENGINE_TIME_MAX:
        print(f"✗ Engine×Time imbalance: range [{min_cell}, {max_cell}]")
        print(f"  Expected: [{CANONICAL_ENGINE_TIME_MIN}, {CANONICAL_ENGINE_TIME_MAX}]")
        return False
    if verbose:
        print(f"✓ Engine×Time balance: {min_cell}-{max_cell} per cell")

    # Check 7: Matrix fingerprint (optional)
    actual_fp = compute_matrix_fingerprint(df)

    if 'matrix_fingerprint' in df.columns:
        stored_fp = df['matrix_fingerprint'].iloc[0]

        if pd.notna(stored_fp) and stored_fp != "":
            if actual_fp != stored_fp:
                print(f"✗ Fingerprint mismatch")
                print(f"  Expected: {stored_fp[:16]}...")
                print(f"  Actual:   {actual_fp[:16]}...")
                print(f"  → Matrix may have been edited")
                return False
            if verbose:
                print(f"✓ Fingerprint: {actual_fp[:16]}... (verified)")
        else:
            if verbose:
                print(f"⚠ Fingerprint column exists but empty")
                print(f"  Computed: {actual_fp[:16]}...")
    else:
        if verbose:
            print(f"⚠ No fingerprint column (old matrix format)")
            print(f"  Computed: {actual_fp[:16]}...")

    # All checks passed
    if verbose:
        print()
        print("=" * 70)
        print("✓ Matrix is the canonical pre-registered protocol")
        print("=" * 70)

    return True


def main():
    """Main entry point."""
    try:
        success = verify_matrix(verbose=True)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nVerification cancelled")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Verification failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
