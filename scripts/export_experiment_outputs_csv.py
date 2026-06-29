#!/usr/bin/env python3
"""Export experiment metadata and generated outputs into one validation CSV.

This script reads the canonical experiment matrix and appends the generated
material text from each row's output_path. It is intended for human validation
workflows where reviewers need metadata and the generated material in one file.
"""

import argparse
import csv
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_EXPERIMENTS_CSV = PROJECT_ROOT / "results" / "experiments.csv"
DEFAULT_OUTPUT_CSV = PROJECT_ROOT / "results" / "experiment_outputs_for_validation.csv"

APPENDED_FIELDS = [
    "resolved_output_path",
    "output_file_exists",
    "output_read_error",
    "output_text_chars",
    "output_text_sha256",
    "output_text",
    "exported_at_utc",
]

PROMPT_FIELDS = [
    "prompt_file_exists",
    "prompt_read_error",
    "prompt_text_chars",
    "prompt_text",
]


def project_relative(path: Path) -> str:
    """Return a stable project-relative path when possible."""
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def resolve_path(path_value: str) -> Optional[Path]:
    """Resolve a possibly project-relative path string."""
    if not path_value:
        return None

    path = Path(path_value)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def output_candidates(row: Dict[str, str]) -> Iterable[Path]:
    """Yield output paths in preferred order."""
    seen = set()

    explicit = resolve_path(row.get("output_path", ""))
    if explicit is not None:
        seen.add(explicit)
        yield explicit

    run_id = row.get("run_id", "")
    if run_id:
        fallback = PROJECT_ROOT / "outputs" / f"{run_id}.txt"
        if fallback not in seen:
            yield fallback


def read_first_existing_output(row: Dict[str, str]) -> Tuple[Optional[Path], bool, str, str]:
    """Read output text for an experiment row.

    Returns:
        (resolved_path, exists, error_message, text)
    """
    last_path = None

    for candidate in output_candidates(row):
        last_path = candidate
        if not candidate.exists():
            continue

        try:
            return candidate, True, "", candidate.read_text(encoding="utf-8")
        except Exception as exc:
            return candidate, True, str(exc), ""

    return last_path, False, "output file not found", ""


def read_optional_prompt(row: Dict[str, str]) -> Dict[str, str]:
    """Read prompt text when requested."""
    prompt_path = resolve_path(row.get("prompt_text_path", ""))
    if prompt_path is None:
        return {
            "prompt_file_exists": "False",
            "prompt_read_error": "prompt_text_path is empty",
            "prompt_text_chars": "0",
            "prompt_text": "",
        }

    if not prompt_path.exists():
        return {
            "prompt_file_exists": "False",
            "prompt_read_error": "prompt file not found",
            "prompt_text_chars": "0",
            "prompt_text": "",
        }

    try:
        prompt_text = prompt_path.read_text(encoding="utf-8")
    except Exception as exc:
        return {
            "prompt_file_exists": "True",
            "prompt_read_error": str(exc),
            "prompt_text_chars": "0",
            "prompt_text": "",
        }

    return {
        "prompt_file_exists": "True",
        "prompt_read_error": "",
        "prompt_text_chars": str(len(prompt_text)),
        "prompt_text": prompt_text,
    }


def should_include_status(row: Dict[str, str], statuses: Optional[List[str]]) -> bool:
    """Return whether row status matches requested filters."""
    if not statuses:
        return True
    return row.get("status", "") in statuses


def truncate_text(text: str, max_chars: Optional[int]) -> str:
    """Optionally truncate text for reviewer-friendly preview exports."""
    if max_chars is None or max_chars < 0 or len(text) <= max_chars:
        return text
    return text[:max_chars]


def export_outputs(
    experiments_csv: Path,
    output_csv: Path,
    statuses: Optional[List[str]],
    include_missing: bool,
    include_prompts: bool,
    max_output_chars: Optional[int],
) -> Dict[str, int]:
    """Export experiment rows with material text appended."""
    if not experiments_csv.exists():
        raise FileNotFoundError(f"Experiments CSV not found: {experiments_csv}")

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    exported_at = datetime.now(timezone.utc).isoformat()

    stats = {
        "rows_seen": 0,
        "rows_status_skipped": 0,
        "rows_missing_skipped": 0,
        "rows_exported": 0,
        "rows_with_output": 0,
        "rows_with_read_errors": 0,
    }

    with experiments_csv.open("r", newline="", encoding="utf-8") as input_file:
        reader = csv.DictReader(input_file)
        if reader.fieldnames is None:
            raise ValueError(f"Experiments CSV has no header: {experiments_csv}")

        fieldnames = list(reader.fieldnames)
        for field in APPENDED_FIELDS:
            if field not in fieldnames:
                fieldnames.append(field)
        if include_prompts:
            for field in PROMPT_FIELDS:
                if field not in fieldnames:
                    fieldnames.append(field)

        with output_csv.open("w", newline="", encoding="utf-8") as output_file:
            writer = csv.DictWriter(output_file, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()

            for row in reader:
                stats["rows_seen"] += 1

                if not should_include_status(row, statuses):
                    stats["rows_status_skipped"] += 1
                    continue

                resolved_path, exists, error, output_text = read_first_existing_output(row)
                if exists:
                    stats["rows_with_output"] += 1
                if error and exists:
                    stats["rows_with_read_errors"] += 1

                if not exists and not include_missing:
                    stats["rows_missing_skipped"] += 1
                    continue

                full_output_text = output_text
                row.update({
                    "resolved_output_path": project_relative(resolved_path) if resolved_path else "",
                    "output_file_exists": str(exists),
                    "output_read_error": error,
                    "output_text_chars": str(len(full_output_text)),
                    "output_text_sha256": hashlib.sha256(
                        full_output_text.encode("utf-8")
                    ).hexdigest() if full_output_text else "",
                    "output_text": truncate_text(full_output_text, max_output_chars),
                    "exported_at_utc": exported_at,
                })

                if include_prompts:
                    row.update(read_optional_prompt(row))

                writer.writerow(row)
                stats["rows_exported"] += 1

    return stats


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Export experiment metadata and generated outputs into one CSV."
    )
    parser.add_argument(
        "--experiments",
        default=str(DEFAULT_EXPERIMENTS_CSV),
        help="Path to experiments.csv",
    )
    parser.add_argument(
        "--out",
        default=str(DEFAULT_OUTPUT_CSV),
        help="Output CSV path",
    )
    parser.add_argument(
        "--status",
        action="append",
        help=(
            "Only export rows with this status. Can be passed multiple times. "
            "Default: no status filter."
        ),
    )
    parser.add_argument(
        "--include-missing",
        action="store_true",
        help="Include experiment rows even when the output file is missing.",
    )
    parser.add_argument(
        "--include-prompts",
        action="store_true",
        help="Append prompt_text from prompt_text_path as well as output_text.",
    )
    parser.add_argument(
        "--max-output-chars",
        type=int,
        default=None,
        help="Optional max characters to write in output_text; metadata keeps full char count.",
    )
    return parser.parse_args()


def main() -> None:
    """Run the export."""
    args = parse_args()
    stats = export_outputs(
        experiments_csv=resolve_path(args.experiments) or Path(args.experiments),
        output_csv=resolve_path(args.out) or Path(args.out),
        statuses=args.status,
        include_missing=args.include_missing,
        include_prompts=args.include_prompts,
        max_output_chars=args.max_output_chars,
    )

    print("=" * 80)
    print("EXPERIMENT OUTPUT CSV EXPORT")
    print("=" * 80)
    print(f"Rows seen:              {stats['rows_seen']}")
    print(f"Rows exported:          {stats['rows_exported']}")
    print(f"Rows with output files: {stats['rows_with_output']}")
    print(f"Rows skipped by status: {stats['rows_status_skipped']}")
    print(f"Rows skipped missing:   {stats['rows_missing_skipped']}")
    print(f"Rows with read errors:  {stats['rows_with_read_errors']}")
    print(f"Output CSV:             {args.out}")


if __name__ == "__main__":
    main()
