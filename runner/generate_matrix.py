"""Full matrix generator for experimental runs with randomization."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional
import itertools
import random

import typer

import config as study_config
from config import (
    PRODUCTS, MATERIALS, TIMES, TEMPS, REPS, ENGINES, REGION,
    DEFAULT_MAX_TOKENS, DEFAULT_SEED, DEFAULT_TOP_P,
    DEFAULT_FREQUENCY_PENALTY, DEFAULT_PRESENCE_PENALTY,
    DEFAULT_ACCOUNT_ID
)
from runner.render import load_product_yaml, render_prompt
from runner.utils import (
    append_row,
    build_config_snapshot,
    compute_config_fingerprint,
    make_run_id,
    write_json_file,
)

app = typer.Typer(help="Generate full experimental matrix with randomization")

CSV_PATH = Path("results/experiments.csv")
METADATA_PATH = Path("results/experiments.meta.json")


def parse_experiment_start(experiment_start_iso: Optional[str]) -> Optional[datetime]:
    """Parse experiment start time to timezone-aware UTC datetime."""
    if not experiment_start_iso:
        return None

    try:
        parsed = datetime.fromisoformat(experiment_start_iso)
    except ValueError as exc:
        raise typer.BadParameter(
            "experiment-start must be ISO 8601, for example 2026-04-03T00:00:00+00:00"
        ) from exc

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)


def generate_temporal_schedule(
    count: int,
    *,
    start_at: datetime,
    duration_hours: float,
    seed: int,
) -> List[datetime]:
    """Assign randomized timestamps within a continuous temporal window."""
    schedule_rng = random.Random(seed)
    duration_seconds = duration_hours * 3600.0

    scheduled = []
    for _ in range(count):
        offset_seconds = schedule_rng.uniform(0.0, duration_seconds)
        scheduled.append(start_at + timedelta(seconds=offset_seconds))

    return scheduled


def get_randomization_mode(randomize: bool, temporal: bool) -> str:
    """Describe how matrix order/scheduling were generated."""
    if temporal:
        return "true_temporal_uniform_window"
    if randomize:
        return "shuffled_order"
    return "sequential"


def build_matrix_metadata(
    *,
    config_fingerprint: str,
    config_snapshot: Dict[str, object],
    expected_total: int,
    randomization_seed: int,
    randomization_mode: str,
    temporal_enabled: bool,
    experiment_start_iso: str,
    duration_hours: float,
    trap_flag: bool,
) -> Dict[str, object]:
    """Build reproducibility metadata for the generated matrix."""
    return {
        "config_fingerprint": config_fingerprint,
        "config_snapshot": config_snapshot,
        "expected_total": expected_total,
        "matrix_randomization_seed": randomization_seed,
        "matrix_randomization_mode": randomization_mode,
        "true_temporal_scheduling": temporal_enabled,
        "experiment_start_iso": experiment_start_iso,
        "temporal_window_hours": duration_hours,
        "trap_flag": trap_flag,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "csv_path": str(CSV_PATH),
    }


def generate_full_matrix(
    dry_run: bool = False,
    trap_flag: bool = False,
    randomize: bool = True,
    seed: int = 42,
    force: bool = False,
    allow_existing_matrix: bool = False,
    temporal: bool = False,
    experiment_start_iso: Optional[str] = None,
    duration_hours: float = 72.0,
) -> None:
    """Generate full experimental matrix with optional randomization.

    Args:
        dry_run: If True, compute first 5 run_ids without file writes
        trap_flag: If True, generate trap batch with bias-inducing prompts
        randomize: If True, shuffle run order (recommended for temporal validity)
        seed: Random seed for reproducibility (default: 42)
        force: If True, replace existing matrix/metadata files
        allow_existing_matrix: If True, append compatible rows to existing matrix
        temporal: If True, assign randomized execution timestamps
        experiment_start_iso: Optional ISO 8601 start time for temporal schedule
        duration_hours: Temporal scheduling window
    """
    # Create output directories
    outputs_dir = Path("outputs")
    results_dir = Path("results")

    if not dry_run:
        outputs_dir.mkdir(parents=True, exist_ok=True)
        results_dir.mkdir(parents=True, exist_ok=True)

    if not dry_run and CSV_PATH.exists():
        if force:
            CSV_PATH.unlink()
            if METADATA_PATH.exists():
                METADATA_PATH.unlink()
        elif not allow_existing_matrix:
            typer.echo(
                f"Error: {CSV_PATH} already exists. Refusing to append to an existing matrix.\n"
                "Re-run with --force to regenerate the matrix intentionally.",
                err=True,
            )
            raise typer.Exit(1)

    experiment_start = parse_experiment_start(experiment_start_iso)
    if temporal and experiment_start is None:
        typer.echo(
            "Error: true temporal scheduling requires --experiment-start in ISO 8601 format.",
            err=True,
        )
        raise typer.Exit(1)

    config_snapshot = build_config_snapshot(
        products=PRODUCTS,
        materials=MATERIALS,
        times=TIMES,
        temps=TEMPS,
        reps=REPS,
        engines=ENGINES,
        region=REGION,
        extra={
            "default_account_id": DEFAULT_ACCOUNT_ID,
            "default_max_tokens": DEFAULT_MAX_TOKENS,
            "randomize": randomize,
            "trap_flag": trap_flag,
            "true_temporal_scheduling": temporal,
            "temporal_window_hours": duration_hours,
            "experiment_start_iso": experiment_start.isoformat() if experiment_start else "",
        },
    )
    config_fingerprint = compute_config_fingerprint(config_snapshot)

    # Collision detection set
    seen_run_ids = set()

    # Generate all combinations first (Cartesian product)
    all_combinations = list(itertools.product(
        PRODUCTS, MATERIALS, TIMES, TEMPS, REPS, ENGINES
    ))

    # RANDOMIZATION: Shuffle execution order for temporal validity
    if randomize:
        random.seed(seed)
        random.shuffle(all_combinations)
        if not dry_run:
            typer.echo(f"✓ Randomized {len(all_combinations)} runs (seed={seed})")

    scheduled_datetimes: List[Optional[datetime]] = [None] * len(all_combinations)
    if temporal and experiment_start is not None:
        scheduled_datetimes = generate_temporal_schedule(
            len(all_combinations),
            start_at=experiment_start,
            duration_hours=duration_hours,
            seed=seed + 1_000_003,
        )
        if not dry_run:
            typer.echo(
                f"✓ Assigned randomized schedule across {duration_hours:.1f} hours "
                f"starting {experiment_start.isoformat()}"
            )

    randomization_mode = get_randomization_mode(randomize=randomize, temporal=temporal)

    # Iterate over combinations (randomized or sequential)
    total_runs = 0
    for index, combination in enumerate(all_combinations):
        product_id, material, time_of_day, temp, rep, engine = combination
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
        scheduled_datetime = scheduled_datetimes[index]
        scheduled_datetime_iso = (
            scheduled_datetime.isoformat().replace("+00:00", "Z")
            if scheduled_datetime is not None
            else ""
        )
        scheduled_hour_of_day = scheduled_datetime.hour if scheduled_datetime else ""
        scheduled_day_of_week = scheduled_datetime.strftime("%A") if scheduled_datetime else ""

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
            "scheduled_datetime": scheduled_datetime_iso,
            "scheduled_hour_of_day": scheduled_hour_of_day,
            "scheduled_day_of_week": scheduled_day_of_week,
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

            # Experimental Design / Reproducibility (4)
            "trap_flag": trap_flag,
            "matrix_randomization_seed": seed,
            "matrix_randomization_mode": randomization_mode,
            "config_fingerprint": config_fingerprint,
        }

        append_row(row, path="results/experiments.csv")

        total_runs += 1

    if not dry_run:
        metadata = build_matrix_metadata(
            config_fingerprint=config_fingerprint,
            config_snapshot=config_snapshot,
            expected_total=total_runs,
            randomization_seed=seed,
            randomization_mode=randomization_mode,
            temporal_enabled=temporal,
            experiment_start_iso=experiment_start.isoformat() if experiment_start else "",
            duration_hours=duration_hours,
            trap_flag=trap_flag,
        )
        write_json_file(metadata, str(METADATA_PATH))
        typer.echo(f"Generated {total_runs} jobs. No collisions.")
        typer.echo(f"CSV index: results/experiments.csv")
        typer.echo(f"Matrix metadata: {METADATA_PATH}")
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
    no_randomize: bool = typer.Option(
        False, "--no-randomize", help="Disable randomization (NOT RECOMMENDED for temporal studies)"
    ),
    seed: int = typer.Option(
        getattr(study_config, "MATRIX_RANDOMIZATION_SEED", 42),
        "--seed",
        help="Random seed for matrix randomization",
    ),
    force: bool = typer.Option(
        False, "--force", help="Replace an existing matrix instead of refusing to append"
    ),
    true_temporal: bool = typer.Option(
        getattr(study_config, "ENABLE_TRUE_TEMPORAL_SCHEDULING", False),
        "--true-temporal",
        help="Attach randomized execution timestamps across a temporal window",
    ),
    experiment_start: str = typer.Option(
        getattr(study_config, "EXPERIMENT_START_ISO", ""),
        "--experiment-start",
        help="ISO 8601 start timestamp for true temporal scheduling",
    ),
    duration_hours: float = typer.Option(
        getattr(study_config, "TEMPORAL_WINDOW_HOURS", 72.0),
        "--duration-hours",
        help="Length of the temporal scheduling window in hours",
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

    # Randomization mode
    randomize = not no_randomize

    if both:
        typer.echo(
            f"Generating BOTH base and trap batches ({expected_total * 2} total runs)"
        )
        typer.echo(f"Randomization: {'ENABLED' if randomize else 'DISABLED'} (seed={seed})")
        typer.echo(f"\nBase batch (trap_flag=False):")
        generate_full_matrix(
            dry_run=dry_run,
            trap_flag=False,
            randomize=randomize,
            seed=seed,
            force=force,
            allow_existing_matrix=False,
            temporal=true_temporal,
            experiment_start_iso=experiment_start or None,
            duration_hours=duration_hours,
        )
        if not dry_run:
            typer.echo(f"\nTrap batch (trap_flag=True):")
            generate_full_matrix(
                dry_run=dry_run,
                trap_flag=True,
                randomize=randomize,
                seed=seed + 1,
                force=False,
                allow_existing_matrix=True,
                temporal=true_temporal,
                experiment_start_iso=experiment_start or None,
                duration_hours=duration_hours,
            )
    else:
        trap_mode = trap
        typer.echo(
            f"Matrix size: {expected_total} runs "
            f"({len(PRODUCTS)} products × {len(MATERIALS)} materials × "
            f"{len(TIMES)} times × {len(TEMPS)} temps × "
            f"{len(REPS)} reps × {len(ENGINES)} engines)"
        )
        typer.echo(f"Trap flag: {trap_mode}")
        typer.echo(f"Randomization: {'ENABLED (recommended)' if randomize else 'DISABLED (NOT recommended)'} (seed={seed})")

        # Generate matrix
        generate_full_matrix(
            dry_run=dry_run,
            trap_flag=trap_mode,
            randomize=randomize,
            seed=seed,
            force=force,
            allow_existing_matrix=False,
            temporal=true_temporal,
            experiment_start_iso=experiment_start or None,
            duration_hours=duration_hours,
        )


if __name__ == "__main__":
    app()
