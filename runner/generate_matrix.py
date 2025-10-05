"""Full matrix generator for 2,025 experimental runs."""

from pathlib import Path
from typing import Optional
import itertools

import typer

from config import PRODUCTS, MATERIALS, TIMES, TEMPS, REPS, ENGINES, REGION
from runner.render import load_product_yaml, render_prompt
from runner.utils import make_run_id, append_row, now_iso

app = typer.Typer(help="Generate full experimental matrix (2,025 runs)")


def generate_full_matrix(dry_run: bool = False) -> None:
    """Generate full 2,025-run experimental matrix.

    Args:
        dry_run: If True, compute first 5 run_ids without file writes
    """
    # Create output directory for placeholder files
    outputs_dir = Path("outputs")
    if not dry_run:
        outputs_dir.mkdir(parents=True, exist_ok=True)

    # Create results directory
    results_dir = Path("results")
    if not dry_run:
        results_dir.mkdir(parents=True, exist_ok=True)

    # Collision detection set
    seen_run_ids = set()

    # Cartesian product over all factors
    total_runs = 0
    for product_id, material, time_of_day, temp, rep, engine in itertools.product(
        PRODUCTS, MATERIALS, TIMES, TEMPS, REPS, ENGINES
    ):
        trap_flag = False  # Base matrix uses trap_flag=False

        # Load product YAML
        product_path = Path("products") / f"{product_id}.yaml"
        try:
            product_yaml = load_product_yaml(product_path)
        except FileNotFoundError:
            typer.echo(
                f"Error: Product file not found: {product_path}", err=True
            )
            raise typer.Exit(1)

        # Render prompt
        try:
            prompt_text = render_prompt(
                product_yaml=product_yaml,
                template_name=material,
                trap_flag=trap_flag,
            )
        except Exception as e:
            typer.echo(
                f"Error rendering {product_id} × {material}: {e}", err=True
            )
            raise typer.Exit(1)

        # Build knobs dict
        knobs = {
            "product_id": product_id,
            "material_type": material,
            "engine": engine,
            "time_of_day_label": time_of_day,
            "temperature_label": str(temp),
            "repetition_id": rep,
            "prompt_template": material,
            "trap_flag": trap_flag,
        }

        # Compute run_id
        run_id = make_run_id(knobs, prompt_text)

        # Collision guard
        if run_id in seen_run_ids:
            typer.echo(f"Error: run_id collision detected: {run_id}", err=True)
            raise typer.Exit(1)
        seen_run_ids.add(run_id)

        # Dry run mode: print first 5 run_ids
        if dry_run:
            if total_runs < 5:
                typer.echo(f"{total_runs + 1}. {run_id}")
            total_runs += 1
            if total_runs == 5:
                return
            continue

        # Write placeholder output file
        output_path = outputs_dir / f"{run_id}.txt"
        output_path.write_text("[PLACEHOLDER OUTPUT]\n", encoding="utf-8")

        # Append metadata row to CSV
        row = {
            "timestamp_utc": now_iso(),
            "product_id": product_id,
            "material_type": material,
            "engine": engine,
            "time_of_day_label": time_of_day,
            "temperature_label": str(temp),
            "repetition_id": rep,
            "prompt_template": material,
            "trap_flag": trap_flag,
            "run_id": run_id,
            "output_path": str(output_path),
            "prompt_len": len(prompt_text),
            "output_len": 0,  # Placeholder
        }

        append_row(row, path="results/results.csv")

        total_runs += 1

    if not dry_run:
        typer.echo(f"Generated {total_runs} jobs. No collisions.")


@app.command()
def main(
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Print first 5 run IDs without creating files"
    ),
) -> None:
    """Generate full experimental matrix (2,025 runs).

    Default: Generate 2,025 placeholder outputs and append rows to results.csv
    --dry-run: Print first 5 run_ids without file writes
    """
    # Verify constants
    expected_total = (
        len(PRODUCTS)
        * len(MATERIALS)
        * len(TIMES)
        * len(TEMPS)
        * len(REPS)
        * len(ENGINES)
    )

    if expected_total != 2025:
        typer.echo(
            f"Error: Expected 2,025 runs but got {expected_total} "
            f"({len(PRODUCTS)} × {len(MATERIALS)} × {len(TIMES)} × "
            f"{len(TEMPS)} × {len(REPS)} × {len(ENGINES)})",
            err=True,
        )
        raise typer.Exit(1)

    # Generate matrix
    generate_full_matrix(dry_run=dry_run)


if __name__ == "__main__":
    app()
