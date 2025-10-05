"""Job runner for executing LLM experiments from results index."""

import csv
import json
from pathlib import Path
from typing import Dict, Any, Optional
import uuid

import typer

from runner.render import load_product_yaml, render_prompt
from runner.engines.openai_client import call_openai
from runner.engines.google_client import call_google
from runner.engines.mistral_client import call_mistral
from runner.utils import now_iso

app = typer.Typer(help="Run LLM experiments and persist outputs")


def call_engine(engine: str, prompt: str, temperature: float) -> Dict[str, Any]:
    """Route to appropriate engine client.

    Args:
        engine: Engine name (openai, google, mistral)
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
    else:
        raise ValueError(f"Unknown engine: {engine}")


def run_single_job(
    run_id: str,
    product_id: str,
    material_type: str,
    engine: str,
    temperature: float,
    trap_flag: bool,
    time_of_day_label: str,
    repetition_id: int,
    session_id: Optional[str] = None,
    account_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute a single experimental run.

    Args:
        run_id: Unique run identifier
        product_id: Product slug
        material_type: Template filename
        engine: LLM engine name
        temperature: Sampling temperature
        trap_flag: Whether trap is enabled
        time_of_day_label: Time period
        repetition_id: Repetition number
        session_id: Optional session identifier
        account_id: Optional account identifier

    Returns:
        Dict with execution metadata

    Raises:
        FileNotFoundError: If product YAML not found
        Exception: If engine call fails
    """
    # Load product YAML
    product_path = Path("products") / f"{product_id}.yaml"
    product_yaml = load_product_yaml(product_path)

    # Render prompt
    prompt_text = render_prompt(
        product_yaml=product_yaml,
        template_name=material_type,
        trap_flag=trap_flag,
    )

    # Call engine
    response = call_engine(engine=engine, prompt=prompt_text, temperature=temperature)

    # Persist prompt
    prompts_dir = Path("outputs/prompts")
    prompts_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = prompts_dir / f"{run_id}.txt"
    prompt_path.write_text(prompt_text, encoding="utf-8")

    # Persist output
    outputs_dir = Path("outputs")
    outputs_dir.mkdir(parents=True, exist_ok=True)
    output_path = outputs_dir / f"{run_id}.txt"
    output_path.write_text(response["output_text"], encoding="utf-8")

    # Build result row
    result = {
        "timestamp_utc": now_iso(),
        "session_id": session_id or "",
        "account_id": account_id or "",
        "engine": engine,
        "model": response.get("model", ""),
        "temperature": temperature,
        "time_of_day_label": time_of_day_label,
        "repetition_id": repetition_id,
        "product_id": product_id,
        "material_type": material_type,
        "trap_flag": trap_flag,
        "run_id": run_id,
        "prompt_len": len(prompt_text),
        "output_len": len(response["output_text"]),
        "prompt_tokens": response.get("prompt_tokens", 0),
        "completion_tokens": response.get("completion_tokens", 0),
        "total_tokens": response.get("total_tokens", 0),
        "finish_reason": response.get("finish_reason", ""),
        "prompt_path": str(prompt_path),
        "output_path": str(output_path),
    }

    return result


@app.command()
def run(
    run_id: str = typer.Option(..., help="Run ID from results.csv"),
    product_id: str = typer.Option(..., help="Product slug"),
    material_type: str = typer.Option(..., help="Material template filename"),
    engine: str = typer.Option(..., help="Engine name (openai/google/mistral)"),
    temperature: float = typer.Option(..., help="Sampling temperature"),
    trap_flag: bool = typer.Option(False, help="Enable trap flag"),
    time_of_day_label: str = typer.Option("morning", help="Time of day label"),
    repetition_id: int = typer.Option(1, help="Repetition ID"),
    session_id: Optional[str] = typer.Option(None, help="Session ID"),
    account_id: Optional[str] = typer.Option(None, help="Account ID"),
    results_csv: str = typer.Option(
        "results/results.csv", help="Path to results CSV"
    ),
) -> None:
    """Run a single experiment job."""
    try:
        result = run_single_job(
            run_id=run_id,
            product_id=product_id,
            material_type=material_type,
            engine=engine,
            temperature=temperature,
            trap_flag=trap_flag,
            time_of_day_label=time_of_day_label,
            repetition_id=repetition_id,
            session_id=session_id,
            account_id=account_id,
        )

        # Append to results CSV
        results_path = Path(results_csv)
        file_exists = results_path.exists()

        with open(results_path, "a", newline="", encoding="utf-8") as f:
            fieldnames = list(result.keys())
            writer = csv.DictWriter(f, fieldnames=fieldnames)

            if not file_exists:
                writer.writeheader()

            writer.writerow(result)

        typer.echo(f"✓ Completed run_id={run_id}")

    except Exception as e:
        typer.echo(f"✗ Failed run_id={run_id}: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def batch(
    from_index: str = typer.Option(
        "results/results.csv", help="Path to results CSV index"
    ),
    engine: Optional[str] = typer.Option(
        None, help="Filter to specific engine (optional)"
    ),
    session_id: Optional[str] = typer.Option(None, help="Session ID for all runs"),
    account_id: Optional[str] = typer.Option(None, help="Account ID for all runs"),
    dry_run: bool = typer.Option(False, help="Print pending runs without executing"),
) -> None:
    """Execute all jobs lacking output from results index.

    Reads results.csv, identifies rows where output_len=0 or output_path is missing,
    and executes those jobs.
    """
    index_path = Path(from_index)

    if not index_path.exists():
        typer.echo(f"Error: Index file not found: {index_path}", err=True)
        raise typer.Exit(1)

    # Read index
    with open(index_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Filter pending jobs (output_len == 0 or missing)
    pending = []
    for row in rows:
        # Filter by engine if specified
        if engine and row.get("engine") != engine:
            continue

        # Check if output exists
        output_len = int(row.get("output_len", 0))
        output_path = row.get("output_path", "")

        if output_len == 0 or not Path(output_path).exists():
            pending.append(row)

    typer.echo(f"Found {len(pending)} pending jobs (of {len(rows)} total)")

    if dry_run:
        typer.echo("\nFirst 5 pending jobs:")
        for row in pending[:5]:
            typer.echo(
                f"  run_id={row['run_id']} "
                f"product={row['product_id']} "
                f"engine={row['engine']}"
            )
        return

    # Execute pending jobs
    completed = 0
    failed = 0

    for i, row in enumerate(pending, 1):
        typer.echo(f"\n[{i}/{len(pending)}] Processing run_id={row['run_id']}")

        try:
            result = run_single_job(
                run_id=row["run_id"],
                product_id=row["product_id"],
                material_type=row.get("material_type", row.get("prompt_template")),
                engine=row["engine"],
                temperature=float(row.get("temperature_label", row.get("temperature"))),
                trap_flag=row.get("trap_flag", "False").lower() == "true",
                time_of_day_label=row.get("time_of_day_label", "morning"),
                repetition_id=int(row.get("repetition_id", 1)),
                session_id=session_id,
                account_id=account_id,
            )

            # Update the row in-memory
            row.update(result)
            completed += 1

        except Exception as e:
            typer.echo(f"✗ Failed: {e}", err=True)
            failed += 1

    # Write updated results back to CSV
    typer.echo(f"\n Writing updated results to {index_path}")
    with open(index_path, "w", newline="", encoding="utf-8") as f:
        if rows:
            fieldnames = list(rows[0].keys())
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    typer.echo(f"\n✓ Completed: {completed}")
    typer.echo(f"✗ Failed: {failed}")


if __name__ == "__main__":
    app()
