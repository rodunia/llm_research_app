"""Generate stratified sample for manual labeling."""

import csv
import random
from pathlib import Path
from typing import List, Dict, Any
from collections import defaultdict

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Generate stratified samples for manual validation")
console = Console()


def stratify_sample(
    runs: List[Dict[str, Any]],
    n_per_stratum: int = 22,
    strata_keys: List[str] = None,
) -> List[Dict[str, Any]]:
    """Generate stratified sample from runs.

    Args:
        runs: List of run dictionaries
        n_per_stratum: Target samples per stratum
        strata_keys: Keys to use for stratification (default: engine, product_id)

    Returns:
        List of sampled run dicts
    """
    if strata_keys is None:
        strata_keys = ["engine", "product_id"]

    # Group runs by strata
    strata = defaultdict(list)

    for run in runs:
        # Create stratum key
        stratum = tuple(run.get(key, "") for key in strata_keys)
        strata[stratum].append(run)

    # Sample from each stratum
    sampled = []

    for stratum_key, stratum_runs in strata.items():
        # Sample with replacement if stratum is too small
        sample_size = min(n_per_stratum, len(stratum_runs))

        if sample_size < n_per_stratum:
            console.print(
                f"[yellow]Warning: Stratum {stratum_key} has only {len(stratum_runs)} runs "
                f"(requested {n_per_stratum})[/yellow]"
            )

        sampled_runs = random.sample(stratum_runs, sample_size)
        sampled.extend(sampled_runs)

    return sampled


@app.command()
def main(
    results: str = typer.Option(
        "results/results.csv", help="Path to results CSV"
    ),
    output: str = typer.Option(
        "validation/labels_to_fill.csv", help="Output CSV for manual labels"
    ),
    n_per_stratum: int = typer.Option(
        22, help="Target samples per engine × product stratum"
    ),
    seed: int = typer.Option(42, help="Random seed for reproducibility"),
) -> None:
    """Generate stratified sample for manual validation.

    Creates a CSV with columns:
    - run_id
    - engine
    - product_id
    - material_type
    - time_of_day_label
    - temperature_label
    - repetition_id
    - trap_flag
    - decision (empty, to be filled)
    - notes (empty, to be filled)
    """
    random.seed(seed)

    results_path = Path(results)
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not results_path.exists():
        console.print(f"[red]Error: Results file not found: {results_path}[/red]")
        raise typer.Exit(1)

    # Load results
    with open(results_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        runs = list(reader)

    console.print(f"[cyan]Loaded {len(runs)} runs from {results_path}[/cyan]")

    # Filter to completed runs (output_len > 0)
    completed = [
        run for run in runs if int(run.get("output_len", 0)) > 0
    ]

    console.print(f"[cyan]Found {len(completed)} completed runs[/cyan]")

    if not completed:
        console.print("[red]Error: No completed runs found[/red]")
        raise typer.Exit(1)

    # Stratify sample
    sample = stratify_sample(completed, n_per_stratum=n_per_stratum)

    console.print(f"[green]Sampled {len(sample)} runs for validation[/green]")

    # Write sample CSV
    fieldnames = [
        "run_id",
        "engine",
        "product_id",
        "material_type",
        "time_of_day_label",
        "temperature_label",
        "repetition_id",
        "trap_flag",
        "decision",  # Empty - to be filled manually
        "notes",  # Empty - to be filled manually
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for run in sample:
            writer.writerow(
                {
                    "run_id": run.get("run_id"),
                    "engine": run.get("engine"),
                    "product_id": run.get("product_id"),
                    "material_type": run.get("material_type"),
                    "time_of_day_label": run.get("time_of_day_label"),
                    "temperature_label": run.get("temperature_label"),
                    "repetition_id": run.get("repetition_id"),
                    "trap_flag": run.get("trap_flag"),
                    "decision": "",  # To be filled
                    "notes": "",  # To be filled
                }
            )

    console.print(f"[green]✓ Wrote sample to {output_path}[/green]")

    # Display distribution
    strata_counts = defaultdict(int)
    for run in sample:
        key = (run.get("engine"), run.get("product_id"))
        strata_counts[key] += 1

    table = Table(title="Sample Distribution")
    table.add_column("Engine", style="cyan")
    table.add_column("Product", style="cyan")
    table.add_column("Count", style="bold")

    for (engine, product), count in sorted(strata_counts.items()):
        table.add_row(engine, product, str(count))

    console.print(table)

    console.print(
        f"\n[yellow]Next step: Open {output_path} and fill in 'decision' and 'notes' columns[/yellow]"
    )


if __name__ == "__main__":
    app()
