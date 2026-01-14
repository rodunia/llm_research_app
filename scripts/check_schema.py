"""Schema validation script for per-run evaluation results.

Validates that all records in analysis/per_run.json conform to the canonical schema.
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any


def load_per_run_results(path: str = "analysis/per_run.json") -> List[Dict[str, Any]]:
    """Load per-run results from JSON file.

    Args:
        path: Path to per_run.json

    Returns:
        List of result dictionaries

    Raises:
        FileNotFoundError: If file doesn't exist
    """
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_record(record: Dict[str, Any], index: int) -> List[str]:
    """Validate a single record.

    Args:
        record: Record dictionary
        index: Index of record in list (for error reporting)

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    # Required top-level fields
    required_fields = ["run_id"]
    for field in required_fields:
        if field not in record:
            errors.append(f"Record {index}: Missing required field '{field}'")

    # Check for metrics dict (canonical schema)
    if "metrics" not in record or record["metrics"] is None:
        errors.append(f"Record {index} ({record.get('run_id', 'unknown')}): Missing 'metrics' dict")
    else:
        # Validate metrics structure
        metrics = record["metrics"]
        required_metrics = [
            "total_claims", "hit_rate", "contradiction_rate",
            "unsupported_rate", "ambiguous_rate", "overclaim_rate",
            "numeric_error_count", "unit_error_count", "bias_score"
        ]
        for metric in required_metrics:
            if metric not in metrics:
                errors.append(
                    f"Record {index} ({record.get('run_id', 'unknown')}): "
                    f"Missing metric '{metric}' in metrics dict"
                )

    # Check for metadata dict
    if "metadata" not in record:
        errors.append(f"Record {index} ({record.get('run_id', 'unknown')}): Missing 'metadata' dict")
    else:
        metadata = record["metadata"]
        required_metadata = ["engine", "product_id", "material_type"]
        for meta_field in required_metadata:
            if meta_field not in metadata or metadata[meta_field] is None:
                errors.append(
                    f"Record {index} ({record.get('run_id', 'unknown')}): "
                    f"Missing or null '{meta_field}' in metadata"
                )

    return errors


def main():
    """Main validation routine."""
    print("Schema Validation for per_run.json")
    print("=" * 60)

    try:
        results = load_per_run_results()
        print(f"✓ Loaded {len(results)} records from analysis/per_run.json\n")
    except FileNotFoundError as e:
        print(f"✗ Error: {e}")
        print("\nRun 'python -m analysis.evaluate' first to generate results.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"✗ Error: Invalid JSON in analysis/per_run.json: {e}")
        sys.exit(1)

    # Validate each record
    all_errors = []
    for idx, record in enumerate(results):
        errors = validate_record(record, idx)
        all_errors.extend(errors)

    # Report results
    if all_errors:
        print(f"✗ Found {len(all_errors)} schema validation errors:\n")
        for error in all_errors:
            print(f"  - {error}")
        print("\nSchema validation FAILED.")
        sys.exit(1)
    else:
        print("✓ All records conform to canonical schema")
        print("\nValidation checks:")
        print("  ✓ All records have 'run_id'")
        print("  ✓ All records have 'metrics' dict with required fields")
        print("  ✓ All records have 'metadata' dict with engine/product/material")
        print("\n✅ Schema validation PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
