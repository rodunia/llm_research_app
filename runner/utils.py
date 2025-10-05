"""Utility functions for experiment matrix generation."""

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


def canonical_json(d: dict) -> str:
    """Convert dictionary to canonical JSON string for hashing.

    Args:
        d: Dictionary to convert

    Returns:
        Canonical JSON string with sorted keys, compact format, UTF-8
    """
    return json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def make_run_id(knobs: dict, prompt_text: str) -> str:
    """Generate deterministic run ID from experimental knobs and prompt.

    Args:
        knobs: Dictionary of experimental parameters
        prompt_text: Rendered prompt text

    Returns:
        SHA1 hexdigest of canonical JSON + prompt
    """
    payload = {"knobs": knobs, "prompt": prompt_text}
    canonical = canonical_json(payload)
    hash_obj = hashlib.sha1(canonical.encode("utf-8"))
    return hash_obj.hexdigest()


def now_iso() -> str:
    """Get current UTC timestamp in ISO8601 format with Z suffix.

    Returns:
        ISO8601 timestamp string (e.g., "2025-10-05T14:30:00Z")
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def append_row(row: dict, path: str = "results/results.csv") -> None:
    """Append a row to CSV file, writing header if file doesn't exist.

    Args:
        row: Dictionary of field name -> value
        path: Path to CSV file (created if doesn't exist)
    """
    csv_path = Path(path)
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    file_exists = csv_path.exists()
    mode = "a" if file_exists else "w"

    with open(csv_path, mode=mode, newline="", encoding="utf-8") as f:
        fieldnames = list(row.keys())
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        if not file_exists:
            writer.writeheader()

        writer.writerow(row)
