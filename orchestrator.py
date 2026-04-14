"""Master orchestrator for LLM research experiment pipeline.

This script manages the complete workflow:
1. Generate experimental matrix
2. Execute LLM runs (filtered by time of day)
3. Evaluate outputs
4. Generate analytics
5. Create validation samples

Usage:
    # Manual run (morning subset)
    python orchestrator.py run --time-of-day morning

    # Resume incomplete runs
    python orchestrator.py resume --time-of-day afternoon

    # Analyze completed runs
    python orchestrator.py analyze

    # Generate validation sample
    python orchestrator.py sample

    # Full pipeline
    python orchestrator.py full --time-of-day evening

    # Start scheduler (runs automatically at configured times)
    python orchestrator.py schedule
"""

import sys
import os
import csv
from pathlib import Path
from datetime import datetime, timezone
import subprocess
import time
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

import config as study_config
from config import ENGINES, MATERIALS, PRODUCTS, REGION, REPS, TEMPS, TIMES
from runner.utils import (
    build_config_snapshot,
    compute_config_fingerprint,
    read_json_file,
)

app = typer.Typer(help="Master orchestrator for LLM research experiments")
console = Console()

# Timezone for scheduling (CET)
TIMEZONE = pytz.timezone("Europe/Paris")  # CET/CEST

# Scheduling times (CET)
SCHEDULE_TIMES = {
    "morning": {"hour": 8, "minute": 0},    # 8:00 AM CET
    "afternoon": {"hour": 15, "minute": 0},  # 3:00 PM CET
    "evening": {"hour": 21, "minute": 0},    # 9:00 PM CET
}

MATRIX_METADATA_PATH = Path("results/experiments.meta.json")


def run_command(command: list, description: str) -> bool:
    """Execute a shell command with progress indication.

    Args:
        command: Command and arguments as list
        description: Human-readable description

    Returns:
        True if successful, False otherwise
    """
    console.print(f"\n[cyan]→ {description}[/cyan]")

    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True
        )
        console.print(f"[green]✓ {description} completed[/green]")
        return True
    except subprocess.CalledProcessError as e:
        console.print(f"[red]✗ {description} failed[/red]")
        console.print(f"[red]{e.stderr}[/red]")
        return False


def check_matrix_exists() -> bool:
    """Check if experimental matrix has been generated."""
    return Path("results/experiments.csv").exists()


def build_expected_config_snapshot(
    *,
    randomize: bool = True,
    trap_flag: bool = False,
    temporal: Optional[bool] = None,
    duration_hours: Optional[float] = None,
    experiment_start_iso: Optional[str] = None,
) -> dict:
    """Build the config snapshot the orchestrator expects the matrix to match."""
    temporal_enabled = (
        getattr(study_config, "ENABLE_TRUE_TEMPORAL_SCHEDULING", False)
        if temporal is None
        else temporal
    )
    temporal_window = (
        getattr(study_config, "TEMPORAL_WINDOW_HOURS", 72.0)
        if duration_hours is None
        else duration_hours
    )
    configured_start = (
        getattr(study_config, "EXPERIMENT_START_ISO", "")
        if experiment_start_iso is None
        else experiment_start_iso
    )

    return build_config_snapshot(
        products=PRODUCTS,
        materials=MATERIALS,
        times=TIMES,
        temps=TEMPS,
        reps=REPS,
        engines=ENGINES,
        region=REGION,
        extra={
            "default_account_id": study_config.DEFAULT_ACCOUNT_ID,
            "default_max_tokens": study_config.DEFAULT_MAX_TOKENS,
            "randomize": randomize,
            "trap_flag": trap_flag,
            "true_temporal_scheduling": temporal_enabled,
            "temporal_window_hours": temporal_window,
            "experiment_start_iso": configured_start,
        },
    )


def matrix_matches_expected_config(
    *,
    randomize: bool = True,
    trap_flag: bool = False,
    temporal: Optional[bool] = None,
    duration_hours: Optional[float] = None,
    experiment_start_iso: Optional[str] = None,
) -> bool:
    """Check whether the existing matrix matches the active experiment config."""
    metadata = read_json_file(str(MATRIX_METADATA_PATH))
    if metadata is None:
        console.print(
            f"[red]Matrix metadata missing: {MATRIX_METADATA_PATH}. "
            "Regenerate the matrix before running experiments.[/red]"
        )
        return False

    expected_snapshot = build_expected_config_snapshot(
        randomize=randomize,
        trap_flag=trap_flag,
        temporal=temporal,
        duration_hours=duration_hours,
        experiment_start_iso=experiment_start_iso,
    )
    expected_fingerprint = compute_config_fingerprint(expected_snapshot)
    actual_fingerprint = metadata.get("config_fingerprint", "")

    if expected_fingerprint != actual_fingerprint:
        console.print("[red]Existing matrix does not match the active experiment configuration.[/red]")
        console.print(f"  Expected fingerprint: {expected_fingerprint}")
        console.print(f"  Matrix fingerprint:   {actual_fingerprint}")
        console.print("  Regenerate the matrix intentionally before continuing.")
        return False

    return True


def compute_matrix_fingerprint(df) -> str:
    """Compute SHA256 fingerprint of matrix core columns for integrity checking.

    The fingerprint is based on the randomization-defining columns only
    (not runtime metadata like status, timestamps, tokens).

    This allows detection of any manual editing of the matrix while
    allowing the matrix to be updated with execution results.
    """
    import hashlib
    import pandas as pd

    # Core columns that define the randomization protocol
    # (exclude runtime columns like status, timestamps, tokens)
    core_cols = [
        'run_id', 'product_id', 'material_type', 'engine',
        'temperature', 'time_of_day_label', 'repetition_id',
        'scheduled_datetime', 'scheduled_day_of_week', 'scheduled_hour_of_day'
    ]

    # Only use columns that exist in the dataframe
    available_cols = [col for col in core_cols if col in df.columns]

    if not available_cols:
        return "NO_CORE_COLUMNS"

    # Sort by run_id for deterministic hashing
    core_data = df[available_cols].sort_values('run_id')

    # Compute SHA256 hash
    data_str = core_data.to_csv(index=False)
    return hashlib.sha256(data_str.encode()).hexdigest()


def validate_canonical_matrix() -> bool:
    """Validate that experiments.csv is the canonical pre-registered protocol.

    Checks:
    - Total runs = 1,620
    - Randomization mode = 'stratified_7day_balanced'
    - Seed = 42
    - Engine balance = 540 per engine (±0)
    - Time slot balance = 540 per time slot (±0)
    - Engine×Time balance = 179-181 per cell (stratified remainder distribution)
    - Matrix fingerprint matches (detects manual edits)
    """
    if not check_matrix_exists():
        console.print("[red]✗ No matrix found at results/experiments.csv[/red]")
        return False

    try:
        import pandas as pd
        df = pd.read_csv(Path("results/experiments.csv"))

        # Check 1: Total runs
        if len(df) != 1620:
            console.print(f"[red]✗ Invalid matrix: Expected 1,620 runs, found {len(df)}[/red]")
            return False

        # Check 2: Randomization metadata (MUST match canonical protocol)
        if 'matrix_randomization_mode' in df.columns:
            mode = df['matrix_randomization_mode'].iloc[0]
            if mode != 'stratified_7day_balanced':
                console.print(f"[red]✗ Invalid randomization mode: '{mode}'[/red]")
                console.print("[red]  Expected: 'stratified_7day_balanced' (canonical protocol)[/red]")
                return False
        else:
            console.print("[red]✗ Missing column: 'matrix_randomization_mode'[/red]")
            return False

        if 'matrix_randomization_seed' in df.columns:
            seed = df['matrix_randomization_seed'].iloc[0]
            if seed != 42:
                console.print(f"[red]✗ Invalid seed: {seed}[/red]")
                console.print("[red]  Expected: 42 (canonical protocol)[/red]")
                return False
        else:
            console.print("[red]✗ Missing column: 'matrix_randomization_seed'[/red]")
            return False

        # Check 3: Engine balance (must be exact)
        engine_counts = df['engine'].value_counts()
        if not all(count == 540 for count in engine_counts.values):
            console.print(f"[red]✗ Invalid engine balance: {engine_counts.to_dict()}[/red]")
            console.print("[red]  Expected: 540 per engine[/red]")
            return False

        # Check 4: Time slot balance (must be exact)
        time_counts = df['time_of_day_label'].value_counts()
        if not all(count == 540 for count in time_counts.values):
            console.print(f"[red]✗ Invalid time slot balance: {time_counts.to_dict()}[/red]")
            console.print("[red]  Expected: 540 per time slot[/red]")
            return False

        # Check 5: Engine×Time balance (stratified: 179-181 per cell)
        crosstab = pd.crosstab(df['engine'], df['time_of_day_label'])
        min_cell = crosstab.min().min()
        max_cell = crosstab.max().max()

        if min_cell < 179 or max_cell > 181:
            console.print(f"[red]✗ Invalid engine×time balance: range [{min_cell}, {max_cell}][/red]")
            console.print("[red]  Expected: 179-181 per engine×time cell (stratified distribution)[/red]")
            return False

        # Check 6: Matrix fingerprint (detects manual editing)
        # Note: This check is optional for backward compatibility with matrices
        # generated before fingerprint validation was added
        actual_fingerprint = compute_matrix_fingerprint(df)

        # Check if matrix has stored fingerprint
        if 'matrix_fingerprint' in df.columns:
            stored_fingerprint = df['matrix_fingerprint'].iloc[0]

            if pd.notna(stored_fingerprint) and stored_fingerprint != "":
                if actual_fingerprint != stored_fingerprint:
                    console.print(f"[red]✗ Matrix fingerprint mismatch[/red]")
                    console.print(f"[red]  Expected: {stored_fingerprint[:16]}...[/red]")
                    console.print(f"[red]  Actual:   {actual_fingerprint[:16]}...[/red]")
                    console.print(f"[red]  Matrix may have been manually edited after generation[/red]")
                    return False
        else:
            # Fingerprint column missing - matrix generated before fingerprint was added
            # Show warning but don't fail (backward compatibility)
            console.print(f"[yellow]⚠ Matrix fingerprint not found (old matrix format)[/yellow]")
            console.print(f"[yellow]  Computed fingerprint: {actual_fingerprint[:16]}...[/yellow]")
            console.print(f"[yellow]  Consider regenerating matrix for full provenance protection[/yellow]")

        console.print("[green]✓ Matrix validated as canonical protocol (1,620 runs, seed 42, stratified balance)[/green]")
        return True

    except Exception as e:
        console.print(f"[red]✗ Matrix validation failed: {e}[/red]")
        return False


def generate_matrix(
    *,
    force: bool = False,
    temporal: Optional[bool] = None,
    experiment_start_iso: Optional[str] = None,
    duration_hours: Optional[float] = None,
) -> bool:
    """Validate pre-registered matrix (generation disabled for research integrity).

    NOTE: Matrix generation is DISABLED. The canonical 1,620-run matrix must be
    pre-generated using the stratified randomizer before experiments begin.

    Parameters:
        force, temporal, experiment_start_iso, duration_hours: OBSOLETE
            These parameters are retained for API compatibility but are not used.
            The pre-registered matrix already contains the temporal schedule.

    Returns:
        True if valid canonical matrix exists, False otherwise
    """
    # MATRIX GENERATION DISABLED - Use pre-registered protocol
    # For academic research rigor, the randomization protocol is pre-generated
    # and locked before experiments begin (pre-registration).
    #
    # To generate the canonical 1,620-run matrix:
    #   python scripts/test_randomizer_stratified.py --seed 42
    #
    # This creates results/experiments.csv with validated statistical balance.
    # The orchestrator then executes runs according to this locked protocol.

    console.print("[yellow]Matrix generation is disabled for research integrity.[/yellow]")
    console.print("[yellow]Pre-registered protocol required. Generate using:[/yellow]")
    console.print("[cyan]  python scripts/test_randomizer_stratified.py --seed 42[/cyan]")
    console.print("")

    # Validate existing matrix
    if not validate_canonical_matrix():
        console.print("")
        console.print("[red]✗ No valid canonical matrix found.[/red]")
        console.print("[yellow]Generate the pre-registered protocol first (see command above)[/yellow]")
        return False

    return True

    # OLD CODE (commented out - on-the-fly generation not allowed)
    # if check_matrix_exists() and not force:
    #     if matrix_matches_expected_config(
    #         temporal=temporal_enabled,
    #         duration_hours=schedule_window,
    #         experiment_start_iso=start_iso,
    #     ):
    #         console.print("[yellow]Matrix already exists and matches current config, skipping generation[/yellow]")
    #         return True
    #     return False
    #
    # cmd = [sys.executable, "-m", "runner.generate_matrix"]
    # if force:
    #     cmd.append("--force")
    # if temporal_enabled:
    #     cmd.extend(["--true-temporal", "--experiment-start", start_iso, "--duration-hours", str(schedule_window)])
    #
    # return run_command(cmd, "Generating experimental matrix")


def execute_runs(time_of_day: str = None, session_id: str = None) -> bool:
    """Execute pending LLM runs.

    Args:
        time_of_day: Filter by time of day (morning/afternoon/evening)
        session_id: Optional session identifier

    Returns:
        True if successful
    """
    if not check_matrix_exists():
        console.print("[red]Matrix not found. Run 'generate' first.[/red]")
        return False

    cmd = [sys.executable, "-m", "runner.run_job", "batch"]

    # Pass through --user from ENV var RESEARCH_USER if set (for multi-user claiming)
    user = os.environ.get("RESEARCH_USER")
    if user:
        cmd.extend(["--user", user])

    if time_of_day:
        cmd.extend(["--time-of-day", time_of_day])

    if session_id:
        cmd.extend(["--session-id", session_id])

    description = f"Executing {time_of_day or 'all'} runs"
    return run_command(cmd, description)


def parse_iso_utc(timestamp: str) -> datetime:
    """Parse ISO timestamp with optional trailing Z."""
    normalized = timestamp.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def read_pending_temporal_jobs(
    csv_path: str = "results/experiments.csv",
) -> list[dict]:
    """Read pending jobs that include temporal scheduling metadata."""
    jobs = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("status") != "pending":
                continue
            scheduled_datetime = row.get("scheduled_datetime", "")
            if not scheduled_datetime:
                raise ValueError(
                    "Matrix is missing scheduled_datetime values. Regenerate it with --true-temporal."
                )
            row["_scheduled_dt"] = parse_iso_utc(scheduled_datetime)
            jobs.append(row)

    jobs.sort(key=lambda row: row["_scheduled_dt"])
    return jobs


def evaluate_outputs() -> bool:
    """Run LLM-free evaluation on completed outputs."""
    return run_command(
        [sys.executable, "-m", "analysis.evaluate"],
        "Evaluating outputs"
    )


def generate_analytics() -> bool:
    """Generate analytics reports."""
    return run_command(
        [sys.executable, "-m", "analysis.reporting"],
        "Generating analytics reports"
    )


def create_validation_sample() -> bool:
    """Create stratified sample for manual validation."""
    return run_command(
        [sys.executable, "-m", "validation.make_sample"],
        "Creating validation sample"
    )


def extract_claims(engine: str = None, force: bool = False) -> bool:
    """Extract claims from completed outputs using LLM (temp=0).

    Args:
        engine: Filter by engine (openai/google/mistral), or None for all
        force: Re-extract even if claims already exist

    Returns:
        True if successful
    """
    cmd = [sys.executable, "-m", "runner.extract_claims"]

    if engine:
        cmd.extend(["--engine", engine])

    if force:
        cmd.append("--force")

    description = f"Extracting claims ({engine or 'all engines'})"
    return run_command(cmd, description)


def verify_claims(inplace: bool = True) -> bool:
    """Verify extracted claims using DeBERTa NLI.

    Args:
        inplace: Update claim JSON files in-place (default: True)

    Returns:
        True if successful
    """
    cmd = [
        sys.executable, "-m", "analysis.deberta_verify_claims",
        "--in", "outputs/*_claims.json",
        "--products-dir", "products/"
    ]

    if inplace:
        cmd.append("--inplace")
    else:
        cmd.extend(["--out", "results/all_claims_verified.jsonl"])

    return run_command(cmd, "Verifying claims with DeBERTa NLI")


@app.command()
def run(
    time_of_day: str = typer.Option(
        None,
        "--time-of-day",
        "-t",
        help="Time of day filter (morning/afternoon/evening)"
    ),
    session_id: str = typer.Option(
        None,
        "--session-id",
        "-s",
        help="Session identifier"
    )
) -> None:
    """Execute LLM runs for specified time of day.

    This is idempotent - re-running will only execute pending jobs.
    """
    if time_of_day and time_of_day not in ["morning", "afternoon", "evening"]:
        console.print("[red]Invalid time_of_day. Use: morning, afternoon, or evening[/red]")
        raise typer.Exit(1)

    console.print(f"\n[bold]LLM Research Pipeline - Execute Runs[/bold]")
    console.print(f"Time of day: {time_of_day or 'all'}")
    console.print(f"Timestamp: {datetime.now().isoformat()}\n")

    # Step 1: Ensure matrix exists
    if not generate_matrix():
        raise typer.Exit(1)

    # Step 2: Execute runs
    if not execute_runs(time_of_day=time_of_day, session_id=session_id):
        raise typer.Exit(1)

    console.print("\n[bold green]✓ Run execution complete[/bold green]")


@app.command()
def analyze() -> None:
    """Run evaluation and analytics on completed runs."""
    console.print("\n[bold]LLM Research Pipeline - Analysis[/bold]\n")

    # Step 1: Evaluate outputs
    if not evaluate_outputs():
        raise typer.Exit(1)

    # Step 2: Generate analytics
    if not generate_analytics():
        raise typer.Exit(1)

    console.print("\n[bold green]✓ Analysis complete[/bold green]")


@app.command()
def sample() -> None:
    """Generate stratified sample for manual validation."""
    console.print("\n[bold]LLM Research Pipeline - Validation Sampling[/bold]\n")

    if not create_validation_sample():
        raise typer.Exit(1)

    console.print("\n[bold green]✓ Validation sample created[/bold green]")


@app.command()
def full(
    time_of_day: str = typer.Option(
        None,
        "--time-of-day",
        "-t",
        help="Time of day filter (morning/afternoon/evening)"
    ),
    skip_analysis: bool = typer.Option(
        False,
        "--skip-analysis",
        help="Skip evaluation and analytics"
    )
) -> None:
    """Run complete pipeline: generate → execute → evaluate → analyze → sample."""
    console.print("\n[bold]LLM Research Pipeline - Full Run[/bold]")
    console.print(f"Time of day: {time_of_day or 'all'}")
    console.print(f"Timestamp: {datetime.now().isoformat()}\n")

    # Step 1: Generate matrix
    if not generate_matrix():
        raise typer.Exit(1)

    # Step 2: Execute runs
    if not execute_runs(time_of_day=time_of_day):
        raise typer.Exit(1)

    if not skip_analysis:
        # Step 3: Evaluate
        if not evaluate_outputs():
            raise typer.Exit(1)

        # Step 4: Analytics
        if not generate_analytics():
            raise typer.Exit(1)

        # Step 5: Sample
        if not create_validation_sample():
            raise typer.Exit(1)

    console.print("\n[bold green]✓ Full pipeline complete[/bold green]")


@app.command()
def schedule() -> None:
    """Start the scheduler to run experiments automatically at configured times.

    Runs:
    - Morning: 8:00 AM CET
    - Afternoon: 3:00 PM CET
    - Evening: 9:00 PM CET
    """
    scheduler = BlockingScheduler(timezone=TIMEZONE)

    # Add morning job
    scheduler.add_job(
        lambda: run_scheduled_job("morning"),
        CronTrigger(
            hour=SCHEDULE_TIMES["morning"]["hour"],
            minute=SCHEDULE_TIMES["morning"]["minute"],
            timezone=TIMEZONE
        ),
        id="morning_run",
        name="Morning LLM Experiments",
        replace_existing=True
    )

    # Add afternoon job
    scheduler.add_job(
        lambda: run_scheduled_job("afternoon"),
        CronTrigger(
            hour=SCHEDULE_TIMES["afternoon"]["hour"],
            minute=SCHEDULE_TIMES["afternoon"]["minute"],
            timezone=TIMEZONE
        ),
        id="afternoon_run",
        name="Afternoon LLM Experiments",
        replace_existing=True
    )

    # Add evening job
    scheduler.add_job(
        lambda: run_scheduled_job("evening"),
        CronTrigger(
            hour=SCHEDULE_TIMES["evening"]["hour"],
            minute=SCHEDULE_TIMES["evening"]["minute"],
            timezone=TIMEZONE
        ),
        id="evening_run",
        name="Evening LLM Experiments",
        replace_existing=True
    )

    console.print("[bold green]Scheduler started[/bold green]")
    console.print("\nScheduled runs:")
    console.print(f"  Morning:   {SCHEDULE_TIMES['morning']['hour']:02d}:{SCHEDULE_TIMES['morning']['minute']:02d} CET")
    console.print(f"  Afternoon: {SCHEDULE_TIMES['afternoon']['hour']:02d}:{SCHEDULE_TIMES['afternoon']['minute']:02d} CET")
    console.print(f"  Evening:   {SCHEDULE_TIMES['evening']['hour']:02d}:{SCHEDULE_TIMES['evening']['minute']:02d} CET")
    console.print("\nPress Ctrl+C to stop\n")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        console.print("\n[yellow]Scheduler stopped[/yellow]")


@app.command()
def temporal(
    session_id: str = typer.Option(
        "temporal_v1",
        "--session-id",
        "-s",
        help="Session identifier for provenance",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Preview the temporal schedule without executing jobs",
    ),
    force_regenerate: bool = typer.Option(
        False,
        "--force-regenerate",
        help="Regenerate the matrix even if files already exist",
    ),
    experiment_start: str = typer.Option(
        getattr(study_config, "EXPERIMENT_START_ISO", ""),
        "--experiment-start",
        help="ISO 8601 start timestamp for temporal scheduling",
    ),
    duration_hours: float = typer.Option(
        getattr(study_config, "TEMPORAL_WINDOW_HOURS", 72.0),
        "--duration-hours",
        help="Length of the temporal scheduling window in hours",
    ),
    poll_interval_sec: int = typer.Option(
        30,
        "--poll-interval-sec",
        help="Maximum polling interval while waiting for future runs",
    ),
) -> None:
    """Execute one pending run at a time according to scheduled_datetime."""
    console.print("\n[bold]LLM Research Pipeline - True Temporal Execution[/bold]")
    console.print(f"Session: {session_id}")
    console.print(f"Dry run: {dry_run}")
    console.print(f"Experiment start: {experiment_start}")
    console.print(f"Duration (hours): {duration_hours}\n")

    if not experiment_start:
        console.print("[red]True temporal execution requires --experiment-start.[/red]")
        raise typer.Exit(1)

    if not generate_matrix(
        force=force_regenerate,
        temporal=True,
        experiment_start_iso=experiment_start,
        duration_hours=duration_hours,
    ):
        raise typer.Exit(1)

    pending_jobs = read_pending_temporal_jobs()
    if not pending_jobs:
        console.print("[yellow]No pending jobs found.[/yellow]")
        return

    first_run = pending_jobs[0]["_scheduled_dt"]
    last_run = pending_jobs[-1]["_scheduled_dt"]
    now_utc = datetime.now(timezone.utc)
    past_due = sum(1 for job in pending_jobs if job["_scheduled_dt"] <= now_utc)

    console.print(f"Found {len(pending_jobs)} pending runs")
    console.print(f"First run: {first_run.isoformat()}")
    console.print(f"Last run:  {last_run.isoformat()}")
    console.print(f"Past due: {past_due} runs")
    console.print(f"Future: {len(pending_jobs) - past_due} runs\n")

    if dry_run:
        console.print("Schedule Preview:")
        for index, job in enumerate(pending_jobs[:10], start=1):
            console.print(
                f"{index}. {job['_scheduled_dt'].isoformat()} - "
                f"{job['run_id'][:12]}... ({job['engine']})"
            )
        return

    while True:
        pending_jobs = read_pending_temporal_jobs()
        if not pending_jobs:
            console.print("\n[bold green]✓ Temporal execution complete[/bold green]")
            return

        now_utc = datetime.now(timezone.utc)
        next_job = pending_jobs[0]
        scheduled_dt = next_job["_scheduled_dt"]

        if scheduled_dt > now_utc:
            sleep_seconds = min((scheduled_dt - now_utc).total_seconds(), poll_interval_sec)
            console.print(
                f"[cyan]Waiting {sleep_seconds:.0f}s for next run at {scheduled_dt.isoformat()}[/cyan]"
            )
            time.sleep(max(sleep_seconds, 1))
            continue

        cmd = [
            sys.executable,
            "-m",
            "runner.run_job",
            "single",
            "--run-id",
            next_job["run_id"],
            "--session-id",
            session_id,
        ]
        if not run_command(cmd, f"Executing scheduled run {next_job['run_id'][:12]}"):
            # Log failure but continue execution (don't kill entire experiment)
            console.print(
                f"[yellow]⚠ Run {next_job['run_id'][:12]} failed, continuing to next run[/yellow]"
            )
            # Failed run is already marked as status='failed' in CSV by run_job.py
            # Temporal will skip it on next loop iteration


def run_scheduled_job(time_of_day: str) -> None:
    """Execute a scheduled job for the specified time of day.

    Args:
        time_of_day: morning, afternoon, or evening
    """
    console.print(f"\n[bold cyan]═══ Scheduled Run: {time_of_day.upper()} ═══[/bold cyan]")
    console.print(f"Timestamp: {datetime.now().isoformat()}\n")

    session_id = f"auto_{time_of_day}_{datetime.now().strftime('%Y%m%d')}"

    try:
        # Generate matrix if needed
        generate_matrix()

        # Execute runs
        execute_runs(time_of_day=time_of_day, session_id=session_id)

        # Run analysis
        evaluate_outputs()
        generate_analytics()

        console.print(f"\n[bold green]✓ {time_of_day.capitalize()} run complete[/bold green]\n")

    except Exception as e:
        console.print(f"\n[bold red]✗ {time_of_day.capitalize()} run failed: {e}[/bold red]\n")


@app.command()
def extract(
    engine: str = typer.Option(
        None,
        "--engine",
        "-e",
        help="Engine to extract from (openai/google/mistral), or all if not specified"
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Re-extract even if claims already exist"
    )
) -> None:
    """Extract claims from completed outputs using LLM (temp=0).

    This runs claim extraction on all completed runs for the specified engine.
    Uses GPT-4o-mini at temperature=0 for reproducible extraction.
    """
    console.print("\n[bold]LLM Research Pipeline - Claim Extraction[/bold]")
    console.print(f"Engine: {engine or 'all'}")
    console.print(f"Force re-extract: {force}\n")

    if not extract_claims(engine=engine, force=force):
        raise typer.Exit(1)

    console.print("\n[bold green]✓ Claim extraction complete[/bold green]")


@app.command()
def verify(
    inplace: bool = typer.Option(
        True,
        "--inplace/--to-file",
        help="Update JSON files in-place (default) or write to separate file"
    )
) -> None:
    """Verify extracted claims using DeBERTa NLI.

    This runs DeBERTa verification on all extracted claims, comparing them
    against the product YAML ground truth (premise).
    """
    console.print("\n[bold]LLM Research Pipeline - Claim Verification[/bold]")
    console.print(f"Mode: {'in-place update' if inplace else 'separate output file'}\n")

    if not verify_claims(inplace=inplace):
        raise typer.Exit(1)

    console.print("\n[bold green]✓ Claim verification complete[/bold green]")


@app.command()
def status() -> None:
    """Show pipeline status and statistics."""
    console.print("\n[bold]Pipeline Status[/bold]\n")

    # Validate canonical matrix first
    if check_matrix_exists():
        if not validate_canonical_matrix():
            console.print("[red]Matrix validation failed. Cannot show status.[/red]")
            raise typer.Exit(1)

    # Check matrix - prefer DB if available, fallback to CSV
    db_path = Path("results/experiments.db")
    if db_path.exists():
        # Read from DB (authoritative runtime state)
        try:
            from runner.job_store import get_status_counts
            counts = get_status_counts(db_path=str(db_path))

            console.print(f"[green]✓[/green] Matrix tracked in DB: {counts['total']} total runs")
            console.print(f"  • Pending: {counts['pending']}")
            console.print(f"  • Claimed: {counts['claimed']}")
            console.print(f"  • Running: {counts['running']}")
            console.print(f"  • Completed: {counts['completed']}")
            console.print(f"  • Failed: {counts['failed']}")
        except Exception as e:
            console.print(f"[yellow]Warning: Could not read DB, falling back to CSV: {e}[/yellow]")
            # Fall through to CSV reading
            db_path = None

    if not db_path or not db_path.exists():
        # Fallback: read from CSV
        if check_matrix_exists():
            import csv
            with open("results/experiments.csv", "r") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                total = len(rows)
                pending = sum(1 for r in rows if r.get("status") == "pending")
                completed = sum(1 for r in rows if r.get("status") == "completed")

            console.print(f"[green]✓[/green] Matrix generated: {total} total runs")
            console.print(f"  • Pending: {pending}")
            console.print(f"  • Completed: {completed}")
        else:
            console.print("[yellow]○[/yellow] Matrix not generated")

    # Check outputs
    outputs_dir = Path("outputs")
    if outputs_dir.exists():
        output_count = len(list(outputs_dir.glob("*.txt")))
        console.print(f"\n[green]✓[/green] Outputs: {output_count} files")

    # Check analysis
    analysis_file = Path("analysis/per_run.json")
    if analysis_file.exists():
        console.print(f"[green]✓[/green] Analysis complete")
    else:
        console.print(f"[yellow]○[/yellow] Analysis not run")

    console.print()


if __name__ == "__main__":
    app()
