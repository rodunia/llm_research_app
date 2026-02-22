"""Utility functions for experiment matrix generation."""

import csv
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
import importlib.metadata


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


def update_csv_row(run_id: str, updates: dict, path: str = "results/experiments.csv") -> bool:
    """Update a row in CSV file by run_id.

    Args:
        run_id: Run ID to update
        updates: Dictionary of field name -> new value
        path: Path to CSV file

    Returns:
        True if row was found and updated, False otherwise
    """
    csv_path = Path(path)
    if not csv_path.exists():
        return False

    # Read all rows
    with open(csv_path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    # Find and update the row
    found = False
    for row in rows:
        if row.get("run_id") == run_id:
            row.update(updates)
            found = True
            break

    if not found:
        return False

    # Write back all rows
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return True


def get_git_hash() -> str:
    """Get current git commit hash.

    Returns:
        Git commit hash (short) or "unknown" if not in a git repo
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "unknown"


def get_package_versions() -> Dict[str, str]:
    """Get versions of key packages.

    Returns:
        Dictionary of package name -> version string
    """
    key_packages = [
        "transformers", "torch", "typer", "pandas", "numpy",
        "rapidfuzz", "pint", "rich", "openai", "anthropic",
        "google-generativeai", "mistralai"
    ]

    versions = {}
    for pkg in key_packages:
        try:
            versions[pkg] = importlib.metadata.version(pkg)
        except importlib.metadata.PackageNotFoundError:
            versions[pkg] = "not_installed"

    return versions


def write_manifest(
    session_id: str,
    config_snapshot: Optional[Dict[str, Any]] = None,
    manifest_dir: str = "results/manifests"
) -> Path:
    """Write a reproducibility manifest for a session.

    Args:
        session_id: Unique session identifier (e.g., "manual_20260114_143000")
        config_snapshot: Optional config dict snapshot (PRODUCTS, MATERIALS, etc.)
        manifest_dir: Directory to write manifests (default: results/manifests)

    Returns:
        Path to written manifest file
    """
    manifest_path = Path(manifest_dir)
    manifest_path.mkdir(parents=True, exist_ok=True)

    manifest_file = manifest_path / f"{session_id}.json"

    # Don't overwrite existing manifests
    if manifest_file.exists():
        # Append a suffix
        counter = 1
        while True:
            manifest_file = manifest_path / f"{session_id}_{counter}.json"
            if not manifest_file.exists():
                break
            counter += 1

    # Build manifest
    manifest = {
        "session_id": session_id,
        "timestamp": now_iso(),
        "git_hash": get_git_hash(),
        "python_version": sys.version,
        "package_versions": get_package_versions(),
    }

    # Add config snapshot if provided
    if config_snapshot:
        manifest["config"] = config_snapshot

    # Write manifest
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    return manifest_file
