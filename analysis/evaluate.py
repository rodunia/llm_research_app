"""CLI for automated LLM-free evaluation of experimental outputs."""

import csv
import json
from pathlib import Path
from typing import List, Dict, Any

import typer
from rich.console import Console
from rich.table import Table

from runner.render import load_product_yaml
from analysis.metrics import Decision, aggregate_metrics
from analysis.bias_screen import (
    screen_output,
    detect_numeric_errors,
    detect_unit_errors,
)

app = typer.Typer(help="Evaluate experimental outputs with LLM-free metrics")
console = Console()


def evaluate_single_run(
    run_id: str,
    output_text: str,
    product_yaml: Dict[str, Any],
) -> Dict[str, Any]:
    """Evaluate a single experimental run.

    Args:
        run_id: Run identifier
        output_text: Generated LLM output
        product_yaml: Product specification dict

    Returns:
        Evaluation results dict
    """
    # Screen for claims
    claim_matches = screen_output(
        output_text=output_text,
        authorized_claims=product_yaml.get("authorized_claims", []),
        prohibited_claims=product_yaml.get(
            "prohibited_or_unsupported_claims", []
        ),
    )

    # Extract decisions
    decisions = [match.decision for match in claim_matches]

    # Calculate metrics
    metrics = aggregate_metrics(decisions)

    # Detect numeric errors
    numeric_errors = detect_numeric_errors(
        output_text=output_text, specs=product_yaml.get("specs", [])
    )

    # Detect unit errors
    unit_errors = detect_unit_errors(
        output_text=output_text, specs=product_yaml.get("specs", [])
    )

    return {
        "run_id": run_id,
        "claim_matches": [
            {
                "decision": match.decision.value,
                "matched_claim": match.matched_claim,
                "claim_type": match.claim_type,
                "confidence": match.confidence,
            }
            for match in claim_matches
        ],
        "metrics": metrics,
        "numeric_errors": numeric_errors,
        "unit_errors": unit_errors,
        "numeric_error_count": len(numeric_errors),
        "unit_error_count": len(unit_errors),
    }


@app.command()
def evaluate(
    results: str = typer.Option(
        "results/results.csv", help="Path to results CSV"
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

    Outputs:
    - analysis/per_run.json: Per-run evaluation results
    - analysis/aggregate.csv: Aggregate metrics by engine × product
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

    console.print(f"[cyan]Loaded {len(runs)} runs from {results_path}[/cyan]")

    # Evaluate each run
    per_run_results = []
    products_cache = {}

    for i, run in enumerate(runs, 1):
        run_id = run.get("run_id")
        product_id = run.get("product_id")
        output_path_str = run.get("output_path", "")

        if not output_path_str:
            console.print(f"[yellow]Skipping run {run_id}: no output_path[/yellow]")
            continue

        output_file = Path(output_path_str)
        if not output_file.exists():
            console.print(
                f"[yellow]Skipping run {run_id}: output file not found[/yellow]"
            )
            continue

        # Load product YAML (cached)
        if product_id not in products_cache:
            product_path = products_dir / f"{product_id}.yaml"
            if not product_path.exists():
                console.print(
                    f"[yellow]Skipping run {run_id}: product YAML not found[/yellow]"
                )
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

            per_run_results.append(result)

            if i % 100 == 0:
                console.print(f"[cyan]Processed {i}/{len(runs)} runs[/cyan]")

        except Exception as e:
            console.print(f"[red]Error evaluating run {run_id}: {e}[/red]")

    # Write per-run results
    per_run_path = output_path / "per_run.json"
    with open(per_run_path, "w", encoding="utf-8") as f:
        json.dump(per_run_results, f, indent=2)

    console.print(f"[green]✓ Wrote per-run results to {per_run_path}[/green]")

    # Aggregate by engine × product
    if aggregate:
        aggregates = {}

        for result in per_run_results:
            key = (result["engine"], result["product_id"])

            if key not in aggregates:
                aggregates[key] = {
                    "engine": result["engine"],
                    "product_id": result["product_id"],
                    "runs": 0,
                    "total_claims": 0,
                    "supported": 0,
                    "contradicted": 0,
                    "unsupported": 0,
                    "ambiguous": 0,
                    "numeric_errors": 0,
                    "unit_errors": 0,
                }

            agg = aggregates[key]
            metrics = result["metrics"]

            agg["runs"] += 1
            agg["total_claims"] += metrics["total_claims"]
            agg["supported"] += int(
                metrics["hit_rate"] * metrics["total_claims"]
            )
            agg["contradicted"] += int(
                metrics["contradiction_rate"] * metrics["total_claims"]
            )
            agg["unsupported"] += int(
                metrics["unsupported_rate"] * metrics["total_claims"]
            )
            agg["ambiguous"] += int(
                metrics["ambiguous_rate"] * metrics["total_claims"]
            )
            agg["numeric_errors"] += result["numeric_error_count"]
            agg["unit_errors"] += result["unit_error_count"]

        # Calculate rates
        for agg in aggregates.values():
            if agg["total_claims"] > 0:
                agg["hit_rate"] = agg["supported"] / agg["total_claims"]
                agg["contradiction_rate"] = (
                    agg["contradicted"] / agg["total_claims"]
                )
                agg["unsupported_rate"] = agg["unsupported"] / agg["total_claims"]
                agg["overclaim_rate"] = (
                    agg["contradicted"] + agg["unsupported"]
                ) / agg["total_claims"]
            else:
                agg["hit_rate"] = 0.0
                agg["contradiction_rate"] = 0.0
                agg["unsupported_rate"] = 0.0
                agg["overclaim_rate"] = 0.0

            agg["numeric_error_rate"] = agg["numeric_errors"] / agg["runs"]
            agg["unit_error_rate"] = agg["unit_errors"] / agg["runs"]

        # Write aggregate CSV
        agg_path = output_path / "aggregate.csv"
        fieldnames = [
            "engine",
            "product_id",
            "runs",
            "total_claims",
            "hit_rate",
            "contradiction_rate",
            "unsupported_rate",
            "overclaim_rate",
            "numeric_error_rate",
            "unit_error_rate",
        ]

        with open(agg_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for agg in aggregates.values():
                writer.writerow(
                    {k: agg.get(k, 0) for k in fieldnames}
                )

        console.print(f"[green]✓ Wrote aggregate metrics to {agg_path}[/green]")

        # Display summary table
        table = Table(title="Aggregate Metrics by Engine × Product")
        table.add_column("Engine", style="cyan")
        table.add_column("Product", style="cyan")
        table.add_column("Runs", style="bold")
        table.add_column("Hit Rate", style="green")
        table.add_column("Overclaim", style="red")

        for agg in sorted(
            aggregates.values(), key=lambda x: (x["engine"], x["product_id"])
        ):
            table.add_row(
                agg["engine"],
                agg["product_id"],
                str(agg["runs"]),
                f"{agg['hit_rate']:.2%}",
                f"{agg['overclaim_rate']:.2%}",
            )

        console.print(table)

    console.print(f"\n[green]✓ Evaluation complete[/green]")


if __name__ == "__main__":
    app()
