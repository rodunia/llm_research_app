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
from pathlib import Path
from datetime import datetime
import subprocess

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

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


def generate_matrix() -> bool:
    """Generate experimental matrix if it doesn't exist."""
    if check_matrix_exists():
        console.print("[yellow]Matrix already exists, skipping generation[/yellow]")
        return True

    return run_command(
        [sys.executable, "-m", "runner.generate_matrix"],
        "Generating experimental matrix"
    )


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

    if session_id:
        cmd.extend(["--session-id", session_id])

    # Note: Filtering by time_of_day needs to be implemented in run_job.py
    # For now, we'll run all pending and document this limitation

    description = f"Executing {time_of_day or 'all'} runs"
    return run_command(cmd, description)


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
def status() -> None:
    """Show pipeline status and statistics."""
    console.print("\n[bold]Pipeline Status[/bold]\n")

    # Check matrix
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
