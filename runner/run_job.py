"""Simple CSV-based job runner for executing LLM experiments."""

import csv
from pathlib import Path
from typing import Dict, Any, Optional, List
import time
from datetime import datetime

import typer
from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn, TimeElapsedColumn

from runner.engines.openai_client import call_openai
from runner.engines.google_client import call_google
from runner.engines.mistral_client import call_mistral
from runner.render import load_product_yaml, render_prompt
from runner.utils import update_csv_row
from config import DEFAULT_MAX_TOKENS, DEFAULT_SEED, DEFAULT_TOP_P, DEFAULT_FREQUENCY_PENALTY, DEFAULT_PRESENCE_PENALTY

app = typer.Typer(help="Run LLM experiments (simple CSV-based)")
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
    """Route to appropriate engine client."""
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
    """Execute a single experimental run and return metadata."""

    # Load product YAML
    product_path = Path("products") / f"{product_id}.yaml"
    product_yaml = load_product_yaml(product_path)

    # Render prompt
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

    # Call engine
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
    execution_duration_sec = (end_time - start_time).total_seconds()
    date_of_run = start_time.strftime("%Y-%m-%d")

    # Save output
    outputs_dir = Path("outputs")
    outputs_dir.mkdir(parents=True, exist_ok=True)
    output_path = outputs_dir / f"{run_id}.txt"
    output_path.write_text(response["output_text"], encoding="utf-8")

    # Return all metadata for CSV update
    return {
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


def read_pending_jobs(
    csv_path: str = "results/experiments.csv",
    time_of_day: Optional[str] = None,
    engine: Optional[str] = None,
    max_jobs: int = 999999
) -> List[Dict[str, Any]]:
    """Read pending jobs from CSV with optional filters."""

    if not Path(csv_path).exists():
        return []

    pending_jobs = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Filter by status
            if row.get('status') != 'pending':
                continue

            # Filter by time_of_day
            if time_of_day and row.get('time_of_day_label') != time_of_day:
                continue

            # Filter by engine
            if engine and row.get('engine') != engine:
                continue

            pending_jobs.append(row)

            if len(pending_jobs) >= max_jobs:
                break

    return pending_jobs


@app.command()
def batch(
    csv_path: str = typer.Option(
        "results/experiments.csv", help="Path to experiments CSV"
    ),
    time_of_day: Optional[str] = typer.Option(
        None, "--time-of-day", "-t", help="Filter by time (morning/afternoon/evening)"
    ),
    engine: Optional[str] = typer.Option(
        None, "--engine", "-e", help="Filter by engine (openai/google/mistral)"
    ),
    max_jobs: int = typer.Option(
        999999, "--max-jobs", help="Maximum number of jobs to run"
    ),
    session_id: Optional[str] = typer.Option(
        None, "--session-id", help="Session identifier for provenance"
    ),
) -> None:
    """Execute pending jobs from CSV (simple, single-user mode)."""

    # Read pending jobs
    console.print(f"[cyan]Reading pending jobs from {csv_path}...[/cyan]")
    pending_jobs = read_pending_jobs(
        csv_path=csv_path,
        time_of_day=time_of_day,
        engine=engine,
        max_jobs=max_jobs
    )

    if not pending_jobs:
        console.print("[yellow]No pending jobs found.[/yellow]")
        return

    console.print(f"[green]Found {len(pending_jobs)} pending jobs[/green]\n")

    # Execute jobs
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
            total=len(pending_jobs)
        )

        for i, job in enumerate(pending_jobs, 1):
            run_id = job["run_id"]
            run_id_short = run_id[:12]
            engine_name = job["engine"]
            product = job["product_id"]

            progress.update(
                task,
                description=f"[cyan]Run {i}/{len(pending_jobs)} | {engine_name} | {product} | {run_id_short}"
            )

            try:
                # Execute job
                result = run_single_job(
                    run_id=run_id,
                    product_id=job["product_id"],
                    material_type=job["material_type"],
                    engine=job["engine"],
                    temperature=float(job.get("temperature", job.get("temperature_label", 0.6))),
                    trap_flag=bool(job.get("trap_flag") == "True" or job.get("trap_flag") == True),
                    max_tokens=int(job.get("max_tokens", DEFAULT_MAX_TOKENS)),
                    seed=int(job["seed"]) if job.get("seed") and job["seed"] != "" else None,
                    top_p=float(job["top_p"]) if job.get("top_p") and job["top_p"] != "" else None,
                    frequency_penalty=float(job["frequency_penalty"]) if job.get("frequency_penalty") and job["frequency_penalty"] != "" else None,
                    presence_penalty=float(job["presence_penalty"]) if job.get("presence_penalty") and job["presence_penalty"] != "" else None,
                    session_id=session_id,
                )

                # Update CSV
                update_csv_row(run_id, result, csv_path)
                completed += 1

            except Exception as e:
                console.print(f"[red]✗ Failed {run_id_short}: {e}[/red]")
                # Mark as failed in CSV
                update_csv_row(run_id, {
                    "status": "failed",
                    "finish_reason": "error",
                    "completed_at": datetime.utcnow().isoformat() + 'Z'
                }, csv_path)
                failed += 1

            progress.advance(task)

    # Summary
    elapsed_time = time.time() - start_time
    avg_time_per_run = elapsed_time / len(pending_jobs) if pending_jobs else 0

    console.print("\n[bold]Execution Summary[/bold]")
    console.print(f"[green]✓ Completed: {completed}[/green]")
    if failed > 0:
        console.print(f"[red]✗ Failed: {failed}[/red]")
    console.print(f"[cyan]⏱ Total time: {elapsed_time:.1f}s ({avg_time_per_run:.1f}s per run)[/cyan]")
    console.print(f"[cyan]📊 Success rate: {(completed / len(pending_jobs) * 100):.1f}%[/cyan]")


if __name__ == "__main__":
    app()
