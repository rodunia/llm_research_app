"""Full matrix generator for 1,620 experimental runs (4 engines)."""

from pathlib import Path
from typing import Optional
import itertools

import typer

from config import (
    PRODUCTS, MATERIALS, TIMES, TEMPS, REPS, ENGINES, REGION,
    DEFAULT_MAX_TOKENS, DEFAULT_SEED, DEFAULT_TOP_P,
    DEFAULT_FREQUENCY_PENALTY, DEFAULT_PRESENCE_PENALTY,
    DEFAULT_ACCOUNT_ID
)
from runner.render import load_product_yaml, render_prompt
from runner.utils import make_run_id, append_row

app = typer.Typer(help="Generate full experimental matrix (1,620 runs)")


def generate_full_matrix(dry_run: bool = False, trap_flag: bool = False) -> None:
    """Generate full experimental matrix (1,215 runs with 3 engines).

    Args:
        dry_run: If True, compute first 5 run_ids without file writes
        trap_flag: If True, generate trap batch with bias-inducing prompts
    """
    # Create output directories
    outputs_dir = Path("outputs")
    results_dir = Path("results")

    if not dry_run:
        outputs_dir.mkdir(parents=True, exist_ok=True)
        results_dir.mkdir(parents=True, exist_ok=True)

    # Collision detection set
    seen_run_ids = set()

    # Cartesian product over all factors
    total_runs = 0
    for product_id, material, time_of_day, temp, rep, engine in itertools.product(
        PRODUCTS, MATERIALS, TIMES, TEMPS, REPS, ENGINES
    ):
        # trap_flag is passed as parameter

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

        # Build knobs dict (deterministic, no timestamps)
        knobs = {
            "product_id": product_id,
            "material_type": material,
            "engine": engine,
            "time_of_day_label": time_of_day,
            "temperature_label": str(temp),
            "repetition_id": rep,
            "trap_flag": trap_flag,
        }

        # Compute deterministic run_id
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

        # Define output file path (no prompt file needed)
        output_path = outputs_dir / f"{run_id}.txt"

        # Note: Output file will be created by run_job.py when experiment executes
        # No placeholder file is created - experiments.csv tracks pending vs completed

        # Generate prompt_id (product_material_v1 format)
        material_base = material.replace('.j2', '')
        prompt_id = f"{product_id}_{material_base}_v1"

        # Prompt text path (will be saved during execution)
        prompt_text_path = f"outputs/prompts/{run_id}.txt"

        # Append metadata row to CSV (complete schema - 31 columns)
        row = {
            # Core Identifiers (4)
            "run_id": run_id,
            "product_id": product_id,
            "material_type": material,
            "engine": engine,

            # Prompt Info (3)
            "prompt_id": prompt_id,
            "prompt_text_path": prompt_text_path,
            "system_prompt": "",  # Will be populated if template uses system prompt

            # Model Setup (8)
            "model": "",  # Populated at runtime from API response
            "model_version": "",  # Populated at runtime from API response
            "temperature": temp,
            "max_tokens": DEFAULT_MAX_TOKENS,
            "seed": DEFAULT_SEED if DEFAULT_SEED is not None else "",
            "top_p": DEFAULT_TOP_P if DEFAULT_TOP_P is not None else "",
            "frequency_penalty": DEFAULT_FREQUENCY_PENALTY if DEFAULT_FREQUENCY_PENALTY is not None else "",
            "presence_penalty": DEFAULT_PRESENCE_PENALTY if DEFAULT_PRESENCE_PENALTY is not None else "",

            # Run Context (6)
            "session_id": "",  # Populated at runtime
            "account_id": DEFAULT_ACCOUNT_ID,
            "time_of_day_label": time_of_day,
            "repetition_id": rep,
            "started_at": "",  # Populated at runtime
            "completed_at": "",  # Populated at runtime

            # Response Data (5)
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "finish_reason": "",
            "output_path": str(output_path),

            # Computed/Derived (3)
            "date_of_run": "",  # Populated at runtime
            "execution_duration_sec": "",  # Populated at runtime
            "status": "pending",

            # Experimental Design (1)
            "trap_flag": trap_flag,
        }

        append_row(row, path="results/experiments.csv")

        total_runs += 1

    if not dry_run:
        typer.echo(f"Generated {total_runs} jobs. No collisions.")
        typer.echo(f"CSV index: results/experiments.csv")
        typer.echo(f"Prompts will be rendered on-the-fly from templates/ + products/")


@app.command()
def main(
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Print first 5 run IDs without creating files"
    ),
    trap: bool = typer.Option(
        False, "--trap", help="Generate trap batch with bias-inducing prompts"
    ),
    both: bool = typer.Option(
        False, "--both", help="Generate both base and trap batches"
    ),
) -> None:
    """Generate experimental matrix.

    Default: Generate base matrix (trap_flag=False)
    --trap: Generate trap batch only (trap_flag=True)
    --both: Generate both base and trap batches
    --dry-run: Print first 5 run_ids without file writes
    """
    # Calculate expected matrix size
    expected_total = (
        len(PRODUCTS)
        * len(MATERIALS)
        * len(TIMES)
        * len(TEMPS)
        * len(REPS)
        * len(ENGINES)
    )

    if both:
        typer.echo(
            f"Generating BOTH base and trap batches ({expected_total * 2} total runs)"
        )
        typer.echo(f"\nBase batch (trap_flag=False):")
        generate_full_matrix(dry_run=dry_run, trap_flag=False)
        if not dry_run:
            typer.echo(f"\nTrap batch (trap_flag=True):")
            generate_full_matrix(dry_run=dry_run, trap_flag=True)
    else:
        trap_mode = trap
        typer.echo(
            f"Matrix size: {expected_total} runs "
            f"({len(PRODUCTS)} products × {len(MATERIALS)} materials × "
            f"{len(TIMES)} times × {len(TEMPS)} temps × "
            f"{len(REPS)} reps × {len(ENGINES)} engines)"
        )
        typer.echo(f"Trap flag: {trap_mode}")

        # Generate matrix
        generate_full_matrix(dry_run=dry_run, trap_flag=trap_mode)


if __name__ == "__main__":
    app()
