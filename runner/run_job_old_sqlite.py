"""Job runner for executing LLM experiments from results index."""

import csv
import os
import socket
from pathlib import Path
from typing import Dict, Any, Optional
import time
from datetime import datetime

import typer
from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn, TimeElapsedColumn

from runner.engines.openai_client import call_openai
from runner.engines.google_client import call_google
from runner.engines.mistral_client import call_mistral
from runner.engines.anthropic_client import call_anthropic
from runner.utils import now_iso
from runner.render import load_product_yaml, render_prompt
from config import DEFAULT_MAX_TOKENS, DEFAULT_SEED, DEFAULT_TOP_P, DEFAULT_FREQUENCY_PENALTY, DEFAULT_PRESENCE_PENALTY
from runner.job_store import (
    initialize_db,
    claim_jobs,
    mark_running,
    mark_completed,
    mark_failed,
    get_job,
    get_status_counts,
    export_status_to_csv
)

app = typer.Typer(help="Run LLM experiments and persist outputs")
console = Console()


def call_engine(
    engine: str,
    prompt: str,
    temperature: float,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    seed: Optional[int] = DEFAULT_SEED,
    top_p: Optional[float] = DEFAULT_TOP_P,
    frequency_penalty: Optional[float] = DEFAULT_FREQUENCY_PENALTY,
    presence_penalty: Optional[float] = DEFAULT_PRESENCE_PENALTY,
) -> Dict[str, Any]:
    """Route to appropriate engine client.

    Args:
        engine: Engine name (openai, google, mistral, anthropic)
        prompt: Prompt text
        temperature: Sampling temperature
        max_tokens: Maximum completion tokens
        seed: Random seed for reproducibility (if supported)
        top_p: Nucleus sampling parameter (if supported)
        frequency_penalty: Repetition penalty (if supported)
        presence_penalty: Token diversity penalty (if supported)

    Returns:
        Engine response dict

    Raises:
        ValueError: If engine is unknown
    """
    # Build kwargs for engine clients
    kwargs = {
        "prompt": prompt,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "seed": seed,
        "top_p": top_p,
        "frequency_penalty": frequency_penalty,
        "presence_penalty": presence_penalty,
    }

    if engine == "openai":
        return call_openai(**kwargs)
    elif engine == "google":
        return call_google(**kwargs)
    elif engine == "mistral":
        return call_mistral(**kwargs)
    elif engine == "anthropic":
        return call_anthropic(**kwargs)
    else:
        raise ValueError(f"Unknown engine: {engine}")


def run_single_job(
    run_id: str,
    product_id: str,
    material_type: str,
    engine: str,
    temperature: float,
    trap_flag: bool = False,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    seed: Optional[int] = DEFAULT_SEED,
    top_p: Optional[float] = DEFAULT_TOP_P,
    frequency_penalty: Optional[float] = DEFAULT_FREQUENCY_PENALTY,
    presence_penalty: Optional[float] = DEFAULT_PRESENCE_PENALTY,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute a single experimental run.

    Args:
        run_id: Unique run identifier
        product_id: Product identifier (e.g., 'smartphone_mid')
        material_type: Material template name (e.g., 'digital_ad.j2')
        engine: LLM engine name
        temperature: Sampling temperature
        trap_flag: Whether this is a trap batch experiment
        max_tokens: Maximum completion tokens
        seed: Random seed for reproducibility
        top_p: Nucleus sampling parameter
        frequency_penalty: Repetition penalty
        presence_penalty: Token diversity penalty
        session_id: Session identifier for grouping runs

    Returns:
        Dict with execution metadata (only fields to update in CSV)

    Raises:
        FileNotFoundError: If product YAML not found
        Exception: If engine call fails
    """
    # Load product YAML
    product_path = Path("products") / f"{product_id}.yaml"
    product_yaml = load_product_yaml(product_path)

    # Render prompt on-the-fly from template + product data
    prompt_text = render_prompt(
        product_yaml=product_yaml,
        template_name=material_type,
        trap_flag=trap_flag
    )

    # Save prompt text to file
    prompts_dir = Path("outputs") / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = prompts_dir / f"{run_id}.txt"
    prompt_path.write_text(prompt_text, encoding="utf-8")

    # Call engine with all parameters
    start_time = datetime.utcnow()
    started_at = start_time.isoformat() + 'Z'

    response = call_engine(
        engine=engine,
        prompt=prompt_text,
        temperature=temperature,
        max_tokens=max_tokens,
        seed=seed,
        top_p=top_p,
        frequency_penalty=frequency_penalty,
        presence_penalty=presence_penalty,
    )

    end_time = datetime.utcnow()
    completed_at = end_time.isoformat() + 'Z'

    # Calculate execution duration
    execution_duration_sec = (end_time - start_time).total_seconds()

    # Extract date from timestamp
    date_of_run = start_time.strftime("%Y-%m-%d")

    # Persist output
    outputs_dir = Path("outputs")
    outputs_dir.mkdir(parents=True, exist_ok=True)
    output_path = outputs_dir / f"{run_id}.txt"
    output_path.write_text(response["output_text"], encoding="utf-8")

    # Return all metadata fields that need updating in CSV
    result = {
        "status": "completed",
        "started_at": started_at,
        "completed_at": completed_at,
        "date_of_run": date_of_run,
        "execution_duration_sec": execution_duration_sec,
        "session_id": session_id or "",
        "model": response.get("model", ""),
        "model_version": response.get("model_version", ""),
        "prompt_tokens": response.get("prompt_tokens", 0),
        "completion_tokens": response.get("completion_tokens", 0),
        "total_tokens": response.get("total_tokens", 0),
        "finish_reason": response.get("finish_reason", ""),
    }

    return result


@app.command()
def run(
    run_id: str = typer.Option(..., help="Run ID from experiments.csv"),
    product_id: str = typer.Option(..., help="Product ID (e.g., smartphone_mid)"),
    material_type: str = typer.Option(..., help="Material template (e.g., digital_ad.j2)"),
    engine: str = typer.Option(..., help="Engine name (openai/google/mistral/anthropic)"),
    temperature: float = typer.Option(..., help="Sampling temperature"),
    trap_flag: bool = typer.Option(False, help="Trap batch flag"),
) -> None:
    """Run a single experiment job (primarily for testing)."""
    try:
        result = run_single_job(
            run_id=run_id,
            product_id=product_id,
            material_type=material_type,
            engine=engine,
            temperature=temperature,
            trap_flag=trap_flag,
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
    user: Optional[str] = typer.Option(
        None, "--user", "-u", help="User identifier (for multi-user claiming)"
    ),
    max_jobs: int = typer.Option(
        999999, "--max-jobs", help="Maximum number of jobs to claim"
    ),
    claim_only: bool = typer.Option(
        False, "--claim-only", help="Claim jobs without executing (for debugging)"
    ),
    db_path: str = typer.Option(
        "results/experiments.db", "--db-path", help="Path to SQLite job database"
    ),
    resume: bool = typer.Option(
        False, "--resume", help="Resume incomplete runs (status != 'completed')"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Print pending runs without executing"
    ),
    session_id: Optional[str] = typer.Option(
        None, "--session-id", help="Session identifier for provenance"
    ),
) -> None:
    """Execute pending jobs using atomic claiming from SQLite job store.

    Uses experiments.db for atomic claiming (concurrency-safe for multi-user execution).
    experiments.csv remains the design matrix; DB is authoritative for runtime state.

    Filters can be combined (e.g., --time-of-day morning --engine openai).
    """
    index_path = Path(from_index)

    if not index_path.exists():
        typer.echo(f"Error: Index file not found: {index_path}", err=True)
        raise typer.Exit(1)

    # Initialize DB from CSV if needed
    typer.echo(f"[cyan]Initializing job database from {index_path}...[/cyan]")
    try:
        initialize_db(csv_path=str(index_path), db_path=db_path)
    except Exception as e:
        typer.echo(f"Error initializing database: {e}", err=True)
        raise typer.Exit(1)

    # Determine user (for claiming)
    if user is None:
        # Default to hostname+pid for single-user backward compatibility
        user = f"{socket.gethostname()}_{os.getpid()}"
        typer.echo(f"[dim]No --user specified, using: {user}[/dim]")

    # Build claim filters
    claim_filters = {}
    if time_of_day:
        claim_filters["time_of_day"] = time_of_day
    if engine:
        claim_filters["engine"] = engine
    if repetition is not None:
        claim_filters["repetition_id"] = repetition

    # Get status counts before claiming
    status_counts = get_status_counts(db_path=db_path, filters=claim_filters)

    # Build filter description
    filters_desc = []
    if time_of_day:
        filters_desc.append(f"time={time_of_day}")
    if engine:
        filters_desc.append(f"engine={engine}")
    if repetition:
        filters_desc.append(f"rep={repetition}")
    filter_str = f" ({', '.join(filters_desc)})" if filters_desc else ""

    typer.echo(f"\n[bold]Job Status{filter_str}:[/bold]")
    typer.echo(f"  Pending: {status_counts['pending']}")
    typer.echo(f"  Running: {status_counts['running']}")
    typer.echo(f"  Completed: {status_counts['completed']}")
    typer.echo(f"  Failed: {status_counts['failed']}")
    typer.echo(f"  Total: {status_counts['total']}\n")

    if dry_run:
        typer.echo("[yellow]Dry-run mode: No jobs will be claimed or executed[/yellow]")
        return

    if status_counts['pending'] == 0:
        typer.echo("[yellow]No pending jobs to claim.[/yellow]")
        return

    # Atomically claim jobs
    claim_limit = min(max_jobs, status_counts['pending'])
    typer.echo(f"[cyan]Claiming up to {claim_limit} jobs for user: {user}...[/cyan]")

    try:
        claimed_run_ids = claim_jobs(
            user=user,
            db_path=db_path,
            filters=claim_filters,
            limit=claim_limit
        )
    except Exception as e:
        typer.echo(f"Error claiming jobs: {e}", err=True)
        raise typer.Exit(1)

    if not claimed_run_ids:
        typer.echo("[yellow]No jobs were claimed (may have been claimed by another user)[/yellow]")
        return

    typer.echo(f"[green]✓ Claimed {len(claimed_run_ids)} jobs[/green]\n")

    if claim_only:
        typer.echo("[yellow]--claim-only mode: Jobs claimed but not executed[/yellow]")
        typer.echo(f"Claimed run_ids: {', '.join(r[:12] for r in claimed_run_ids[:10])}...")
        return

    # Execute claimed jobs
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
            total=len(claimed_run_ids)
        )

        for i, run_id in enumerate(claimed_run_ids, 1):
            # Get job details from DB
            job = get_job(run_id, db_path=db_path)
            if not job:
                console.print(f"[red]✗ Job not found: {run_id}[/red]")
                failed += 1
                progress.advance(task)
                continue

            run_id_short = run_id[:12]
            engine_name = job["engine"]
            product = job["product_id"]

            # Update progress description with current job
            progress.update(
                task,
                description=f"[cyan]Run {i}/{len(claimed_run_ids)} | {engine_name} | {product} | {run_id_short}"
            )

            try:
                # Mark as running
                started_at = now_iso()
                mark_running(run_id, started_at=started_at, session_id=session_id, db_path=db_path)

                # Execute job with all parameters from CSV
                result = run_single_job(
                    run_id=run_id,
                    product_id=job["product_id"],
                    material_type=job["material_type"],
                    engine=job["engine"],
                    temperature=float(job.get("temperature", job.get("temperature_label", 0.6))),
                    trap_flag=bool(job.get("trap_flag", False)),
                    max_tokens=int(job.get("max_tokens", DEFAULT_MAX_TOKENS)),
                    seed=int(job["seed"]) if job.get("seed") and job["seed"] != "" else None,
                    top_p=float(job["top_p"]) if job.get("top_p") and job["top_p"] != "" else None,
                    frequency_penalty=float(job["frequency_penalty"]) if job.get("frequency_penalty") and job["frequency_penalty"] != "" else None,
                    presence_penalty=float(job["presence_penalty"]) if job.get("presence_penalty") and job["presence_penalty"] != "" else None,
                    session_id=session_id,
                )

                # Mark as completed
                completed_at = now_iso()
                mark_completed(run_id, completed_at=completed_at, result=result, db_path=db_path)
                completed += 1

            except Exception as e:
                console.print(f"[red]✗ Failed {run_id_short}: {e}[/red]")
                completed_at = now_iso()
                mark_failed(run_id, error=str(e), completed_at=completed_at, db_path=db_path)
                failed += 1

            # Update progress
            progress.advance(task)

    # Calculate statistics
    elapsed_time = time.time() - start_time
    avg_time_per_run = elapsed_time / len(claimed_run_ids) if claimed_run_ids else 0

    # Export status back to CSV for compatibility
    console.print(f"\n[cyan]Exporting status to {index_path}...[/cyan]")
    try:
        export_status_to_csv(csv_path=str(index_path), db_path=db_path)
    except Exception as e:
        console.print(f"[yellow]Warning: Could not export status to CSV: {e}[/yellow]")

    # Display summary
    console.print("\n[bold]Execution Summary[/bold]")
    console.print(f"[green]✓ Completed: {completed}[/green]")
    if failed > 0:
        console.print(f"[red]✗ Failed: {failed}[/red]")
    console.print(f"[cyan]⏱ Total time: {elapsed_time:.1f}s ({avg_time_per_run:.1f}s per run)[/cyan]")
    console.print(f"[cyan]📊 Success rate: {(completed / len(claimed_run_ids) * 100):.1f}%[/cyan]" if claimed_run_ids else "")


if __name__ == "__main__":
    app()
