"""Job runner for executing LLM experiments from results index."""

import csv
from pathlib import Path
from typing import Dict, Any, Optional
import time

import typer
from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn, TimeElapsedColumn

from runner.engines.openai_client import call_openai
from runner.engines.google_client import call_google
from runner.engines.mistral_client import call_mistral
from runner.engines.anthropic_client import call_anthropic
from runner.utils import now_iso

app = typer.Typer(help="Run LLM experiments and persist outputs")
console = Console()


def call_engine(engine: str, prompt: str, temperature: float) -> Dict[str, Any]:
    """Route to appropriate engine client.

    Args:
        engine: Engine name (openai, google, mistral, anthropic)
        prompt: Prompt text
        temperature: Sampling temperature

    Returns:
        Engine response dict

    Raises:
        ValueError: If engine is unknown
    """
    if engine == "openai":
        return call_openai(prompt=prompt, temperature=temperature)
    elif engine == "google":
        return call_google(prompt=prompt, temperature=temperature)
    elif engine == "mistral":
        return call_mistral(prompt=prompt, temperature=temperature)
    elif engine == "anthropic":
        return call_anthropic(prompt=prompt, temperature=temperature)
    else:
        raise ValueError(f"Unknown engine: {engine}")


def run_single_job(
    run_id: str,
    prompt_path: str,
    engine: str,
    temperature: float,
) -> Dict[str, Any]:
    """Execute a single experimental run.

    Args:
        run_id: Unique run identifier
        prompt_path: Path to pre-rendered prompt file
        engine: LLM engine name
        temperature: Sampling temperature

    Returns:
        Dict with execution metadata (only fields to update in CSV)

    Raises:
        FileNotFoundError: If prompt file not found
        Exception: If engine call fails
    """
    # Read pre-rendered prompt from file
    prompt_file = Path(prompt_path)
    if not prompt_file.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

    prompt_text = prompt_file.read_text(encoding="utf-8")

    # Call engine
    started_at = now_iso()
    response = call_engine(engine=engine, prompt=prompt_text, temperature=temperature)
    completed_at = now_iso()

    # Persist output
    outputs_dir = Path("outputs")
    outputs_dir.mkdir(parents=True, exist_ok=True)
    output_path = outputs_dir / f"{run_id}.txt"
    output_path.write_text(response["output_text"], encoding="utf-8")

    # Return only fields that need updating in CSV
    result = {
        "status": "completed",
        "started_at": started_at,
        "completed_at": completed_at,
        "model": response.get("model", ""),
        "prompt_tokens": response.get("prompt_tokens", 0),
        "completion_tokens": response.get("completion_tokens", 0),
        "total_tokens": response.get("total_tokens", 0),
        "finish_reason": response.get("finish_reason", ""),
    }

    return result


@app.command()
def run(
    run_id: str = typer.Option(..., help="Run ID from experiments.csv"),
    prompt_path: str = typer.Option(..., help="Path to prompt file"),
    engine: str = typer.Option(..., help="Engine name (openai/google/mistral/anthropic)"),
    temperature: float = typer.Option(..., help="Sampling temperature"),
) -> None:
    """Run a single experiment job (primarily for testing)."""
    try:
        result = run_single_job(
            run_id=run_id,
            prompt_path=prompt_path,
            engine=engine,
            temperature=temperature,
        )

        typer.echo(f"✓ Completed run_id={run_id}")
        typer.echo(f"  Model: {result['model']}")
        typer.echo(f"  Tokens: {result['total_tokens']}")
        typer.echo(f"  Finish reason: {result['finish_reason']}")

    except Exception as e:
        typer.echo(f"✗ Failed run_id={run_id}: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def batch(
    from_index: str = typer.Option(
        "results/experiments.csv", help="Path to experiments CSV index"
    ),
    time_of_day: Optional[str] = typer.Option(
        None, "--time-of-day", "-t", help="Filter by time of day (morning/afternoon/evening)"
    ),
    engine: Optional[str] = typer.Option(
        None, "--engine", "-e", help="Filter by engine (openai/google/mistral/anthropic)"
    ),
    repetition: Optional[int] = typer.Option(
        None, "--repetition", "-r", help="Filter by repetition ID (1/2/3)"
    ),
    resume: bool = typer.Option(
        False, "--resume", help="Resume incomplete runs (status != 'completed')"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Print pending runs without executing"
    ),
) -> None:
    """Execute pending jobs from experiments CSV with optional filters.

    Reads experiments.csv, identifies pending jobs (status != 'completed'),
    and executes them with progress tracking. Updates CSV in-place.

    Filters can be combined (e.g., --time-of-day morning --engine openai).
    """
    index_path = Path(from_index)

    if not index_path.exists():
        typer.echo(f"Error: Index file not found: {index_path}", err=True)
        raise typer.Exit(1)

    # Read index
    with open(index_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Filter pending jobs
    pending = []
    for row in rows:
        # Check status
        status = row.get("status", "pending")
        if not resume and status == "completed":
            continue

        # Apply filters
        if time_of_day and row.get("time_of_day_label") != time_of_day:
            continue

        if engine and row.get("engine") != engine:
            continue

        if repetition is not None and int(row.get("repetition_id", 0)) != repetition:
            continue

        # Check if output exists
        output_path = row.get("output_path", "")
        if status != "completed" or not Path(output_path).exists():
            pending.append(row)

    # Build filter description
    filters_desc = []
    if time_of_day:
        filters_desc.append(f"time={time_of_day}")
    if engine:
        filters_desc.append(f"engine={engine}")
    if repetition:
        filters_desc.append(f"rep={repetition}")
    filter_str = f" ({', '.join(filters_desc)})" if filters_desc else ""

    typer.echo(f"Found {len(pending)} pending jobs (of {len(rows)} total){filter_str}")

    if dry_run:
        typer.echo("\nFirst 10 pending jobs:")
        for row in pending[:10]:
            typer.echo(
                f"  {row['run_id'][:12]} | {row['engine']:10} | "
                f"{row['product_id']:20} | {row['material_type']:30} | "
                f"temp={row['temperature_label']} time={row['time_of_day_label']} rep={row['repetition_id']}"
            )
        return

    if not pending:
        typer.echo("No pending jobs to execute.")
        return

    # Execute pending jobs with progress bar
    completed = 0
    failed = 0
    start_time = time.time()

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("•"),
        TextColumn("{task.completed}/{task.total}"),
        TextColumn("•"),
        TimeElapsedColumn(),
        TextColumn("•"),
        TimeRemainingColumn(),
        console=console
    ) as progress:

        task = progress.add_task(
            "[cyan]Executing LLM runs...",
            total=len(pending)
        )

        for i, row in enumerate(pending, 1):
            run_id_short = row['run_id'][:12]
            engine_name = row['engine']
            product = row['product_id']

            # Update progress description with current job
            progress.update(
                task,
                description=f"[cyan]Run {i}/{len(pending)} | {engine_name} | {product} | {run_id_short}"
            )

            try:
                result = run_single_job(
                    run_id=row["run_id"],
                    prompt_path=row["prompt_path"],
                    engine=row["engine"],
                    temperature=float(row["temperature_label"]),
                )

                # Update the row in-memory
                row.update(result)
                completed += 1

            except Exception as e:
                console.print(f"[red]✗ Failed {run_id_short}: {e}[/red]")
                row["status"] = "failed"
                failed += 1

            # Update progress
            progress.advance(task)

    # Calculate statistics
    elapsed_time = time.time() - start_time
    avg_time_per_run = elapsed_time / len(pending) if pending else 0

    # Write updated results back to CSV
    console.print(f"\n[cyan]Writing updated results to {index_path}[/cyan]")
    with open(index_path, "w", newline="", encoding="utf-8") as f:
        if rows:
            fieldnames = list(rows[0].keys())
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    # Display summary
    console.print("\n[bold]Execution Summary[/bold]")
    console.print(f"[green]✓ Completed: {completed}[/green]")
    if failed > 0:
        console.print(f"[red]✗ Failed: {failed}[/red]")
    console.print(f"[cyan]⏱ Total time: {elapsed_time:.1f}s ({avg_time_per_run:.1f}s per run)[/cyan]")
    console.print(f"[cyan]📊 Success rate: {(completed / len(pending) * 100):.1f}%[/cyan]" if pending else "")


if __name__ == "__main__":
    app()
