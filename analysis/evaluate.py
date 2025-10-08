"""CLI for automated LLM-free evaluation of experimental outputs.

Evaluates completed runs from experiments.csv against product specs using:
- Fuzzy claim matching (rapidfuzz)
- Numeric validation with unit conversion (pint)
- Bias detection (lexicon-based)
"""

import csv
import json
from pathlib import Path
from typing import List, Dict, Any

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from runner.render import load_product_yaml
from analysis.metrics import evaluate_output, EvaluationResult
from analysis.bias_screen import detect_bias, calculate_bias_score

app = typer.Typer(help="Evaluate experimental outputs with LLM-free metrics")
console = Console()


def evaluate_single_run(
    run_id: str,
    output_text: str,
    product_yaml: Dict[str, Any],
) -> Dict[str, Any]:
    """Evaluate a single experimental run using enhanced metrics.

    Args:
        run_id: Run identifier
        output_text: Generated LLM output
        product_yaml: Product specification dict

    Returns:
        Evaluation results dict with metrics and bias scores
    """
    # Main evaluation (fuzzy matching, numeric validation, overclaims)
    eval_result = evaluate_output(
        run_id=run_id,
        output_text=output_text,
        product_yaml=product_yaml
    )

    # Bias detection
    bias_detections, severity_counts = detect_bias(output_text)
    bias_score = calculate_bias_score(severity_counts)

    return {
        "run_id": run_id,
        "decision": eval_result.decision.value,
        "hit_rate": eval_result.hit_rate,
        "contradiction_rate": eval_result.contradiction_rate,
        "unsupported_rate": eval_result.unsupported_rate,
        "ambiguous_rate": eval_result.ambiguous_rate,
        "overclaim_rate": eval_result.overclaim_rate,
        "matched_authorized": eval_result.matched_authorized,
        "violated_prohibited": eval_result.violated_prohibited,
        "numeric_errors": eval_result.numeric_errors,
        "unit_errors": eval_result.unit_errors,
        "overclaims": eval_result.overclaims,
        "bias_detections": [
            {
                "pattern": d.pattern,
                "matches": d.matches,
                "severity": d.severity.value,
                "category": d.category
            }
            for d in bias_detections
        ],
        "bias_severity_counts": severity_counts,
        "bias_score": bias_score,
        "details": eval_result.details
    }


@app.command()
def evaluate(
    results: str = typer.Option(
        "results/experiments.csv", help="Path to experiments CSV"
    ),
    products: str = typer.Option("products", help="Path to products directory"),
    output_dir: str = typer.Option(
        "analysis", help="Output directory for evaluation results"
    ),
    aggregate: bool = typer.Option(
        True, help="Compute aggregate metrics by engine × product"
    ),
) -> None:
    """Evaluate all experimental outputs with LLM-free metrics.

    Reads experiments.csv, evaluates completed runs (status='completed'),
    and generates per-run and aggregate metrics.

    Outputs:
    - analysis/per_run.json: Per-run evaluation results
    - analysis/aggregate.csv: Aggregate metrics by engine × product × material
    """
    results_path = Path(results)
    products_dir = Path(products)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    if not results_path.exists():
        console.print(f"[red]Error: Results file not found: {results_path}[/red]")
        raise typer.Exit(1)

    # Load results
    with open(results_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        runs = list(reader)

    # Filter completed runs only
    completed_runs = [r for r in runs if r.get("status") == "completed"]

    console.print(f"[cyan]Loaded {len(runs)} runs ({len(completed_runs)} completed)[/cyan]")

    # Evaluate each run with progress bar
    per_run_results = []
    products_cache = {}
    skipped = 0
    errors = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task(
            f"[cyan]Evaluating {len(completed_runs)} completed runs...",
            total=len(completed_runs)
        )

        for i, run in enumerate(completed_runs, 1):
            run_id = run.get("run_id")
            product_id = run.get("product_id")
            output_path_str = run.get("output_path", "")

            progress.update(task, description=f"[cyan]Evaluating run {i}/{len(completed_runs)}: {run_id[:12]}...")

            if not output_path_str:
                skipped += 1
                progress.advance(task)
                continue

            output_file = Path(output_path_str)
            if not output_file.exists():
                skipped += 1
                progress.advance(task)
                continue

            # Load product YAML (cached)
            if product_id not in products_cache:
                product_path = products_dir / f"{product_id}.yaml"
                if not product_path.exists():
                    skipped += 1
                    progress.advance(task)
                    continue
                products_cache[product_id] = load_product_yaml(product_path)

            product_yaml = products_cache[product_id]

            # Read output
            output_text = output_file.read_text(encoding="utf-8")

            # Evaluate
            try:
                result = evaluate_single_run(
                    run_id=run_id,
                    output_text=output_text,
                    product_yaml=product_yaml,
                )
                # Add run metadata
                result["engine"] = run.get("engine")
                result["product_id"] = product_id
                result["material_type"] = run.get("material_type")
                result["temperature"] = run.get("temperature_label")
                result["time_of_day"] = run.get("time_of_day_label")
                result["repetition_id"] = run.get("repetition_id")

                per_run_results.append(result)

            except Exception as e:
                console.print(f"[red]Error evaluating {run_id[:12]}: {e}[/red]")
                errors += 1

            progress.advance(task)

    console.print(f"\n[cyan]Evaluated: {len(per_run_results)} | Skipped: {skipped} | Errors: {errors}[/cyan]")

    # Write per-run results
    per_run_path = output_path / "per_run.json"
    with open(per_run_path, "w", encoding="utf-8") as f:
        json.dump(per_run_results, f, indent=2)

    console.print(f"[green]✓ Wrote per-run results to {per_run_path}[/green]")

    # Aggregate by engine × product × material
    if aggregate and per_run_results:
        aggregates = {}

        for result in per_run_results:
            key = (result["engine"], result["product_id"], result["material_type"])

            if key not in aggregates:
                aggregates[key] = {
                    "engine": result["engine"],
                    "product_id": result["product_id"],
                    "material_type": result["material_type"],
                    "runs": 0,
                    "hit_rate_sum": 0.0,
                    "contradiction_rate_sum": 0.0,
                    "unsupported_rate_sum": 0.0,
                    "overclaim_rate_sum": 0.0,
                    "numeric_errors": 0,
                    "unit_errors": 0,
                    "bias_score_sum": 0.0,
                    "decisions": {"Supported": 0, "Contradicted": 0, "Unsupported": 0, "Ambiguous": 0}
                }

            agg = aggregates[key]
            agg["runs"] += 1
            agg["hit_rate_sum"] += result["hit_rate"]
            agg["contradiction_rate_sum"] += result["contradiction_rate"]
            agg["unsupported_rate_sum"] += result["unsupported_rate"]
            agg["overclaim_rate_sum"] += result["overclaim_rate"]
            agg["numeric_errors"] += len(result["numeric_errors"])
            agg["unit_errors"] += len(result["unit_errors"])
            agg["bias_score_sum"] += result["bias_score"]
            agg["decisions"][result["decision"]] += 1

        # Calculate averages
        for agg in aggregates.values():
            n = agg["runs"]
            agg["hit_rate"] = agg["hit_rate_sum"] / n
            agg["contradiction_rate"] = agg["contradiction_rate_sum"] / n
            agg["unsupported_rate"] = agg["unsupported_rate_sum"] / n
            agg["overclaim_rate"] = agg["overclaim_rate_sum"] / n
            agg["numeric_error_rate"] = agg["numeric_errors"] / n
            agg["unit_error_rate"] = agg["unit_errors"] / n
            agg["bias_score"] = agg["bias_score_sum"] / n

        # Write aggregate CSV
        agg_path = output_path / "aggregate.csv"
        fieldnames = [
            "engine",
            "product_id",
            "material_type",
            "runs",
            "hit_rate",
            "contradiction_rate",
            "unsupported_rate",
            "overclaim_rate",
            "numeric_error_rate",
            "unit_error_rate",
            "bias_score",
            "decision_supported",
            "decision_contradicted",
            "decision_unsupported",
            "decision_ambiguous"
        ]

        with open(agg_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for agg in aggregates.values():
                writer.writerow({
                    "engine": agg["engine"],
                    "product_id": agg["product_id"],
                    "material_type": agg["material_type"],
                    "runs": agg["runs"],
                    "hit_rate": round(agg["hit_rate"], 4),
                    "contradiction_rate": round(agg["contradiction_rate"], 4),
                    "unsupported_rate": round(agg["unsupported_rate"], 4),
                    "overclaim_rate": round(agg["overclaim_rate"], 4),
                    "numeric_error_rate": round(agg["numeric_error_rate"], 2),
                    "unit_error_rate": round(agg["unit_error_rate"], 2),
                    "bias_score": round(agg["bias_score"], 1),
                    "decision_supported": agg["decisions"]["Supported"],
                    "decision_contradicted": agg["decisions"]["Contradicted"],
                    "decision_unsupported": agg["decisions"]["Unsupported"],
                    "decision_ambiguous": agg["decisions"]["Ambiguous"]
                })

        console.print(f"[green]✓ Wrote aggregate metrics to {agg_path}[/green]")

        # Display summary table (by engine × product)
        engine_product_aggs = {}
        for result in per_run_results:
            key = (result["engine"], result["product_id"])
            if key not in engine_product_aggs:
                engine_product_aggs[key] = {
                    "engine": result["engine"],
                    "product_id": result["product_id"],
                    "runs": 0,
                    "hit_rate_sum": 0.0,
                    "overclaim_rate_sum": 0.0,
                    "bias_score_sum": 0.0
                }
            ep_agg = engine_product_aggs[key]
            ep_agg["runs"] += 1
            ep_agg["hit_rate_sum"] += result["hit_rate"]
            ep_agg["overclaim_rate_sum"] += result["overclaim_rate"]
            ep_agg["bias_score_sum"] += result["bias_score"]

        table = Table(title="Aggregate Metrics by Engine × Product")
        table.add_column("Engine", style="cyan")
        table.add_column("Product", style="cyan")
        table.add_column("Runs", justify="right")
        table.add_column("Hit Rate", style="green", justify="right")
        table.add_column("Overclaim", style="red", justify="right")
        table.add_column("Bias Score", style="yellow", justify="right")

        for ep_agg in sorted(engine_product_aggs.values(), key=lambda x: (x["engine"], x["product_id"])):
            n = ep_agg["runs"]
            table.add_row(
                ep_agg["engine"],
                ep_agg["product_id"],
                str(n),
                f"{ep_agg['hit_rate_sum']/n:.1%}",
                f"{ep_agg['overclaim_rate_sum']/n:.1%}",
                f"{ep_agg['bias_score_sum']/n:.1f}"
            )

        console.print(table)

    console.print(f"\n[green]✓ Evaluation complete[/green]")


if __name__ == "__main__":
    app()
