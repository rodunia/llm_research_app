"""Automated analytics and reporting for LLM experiments.

Generates comprehensive reports including:
- Aggregate metrics by engine × product
- Drift analysis (consistency over repetitions/days)
- Temperature effects
- Time-of-day analysis
- Token usage and cost analysis
"""

import csv
import json
from pathlib import Path
from collections import defaultdict
from typing import List, Dict, Any, Optional

import typer
import pandas as pd
import numpy as np
from scipy import stats
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Generate analytics reports from experimental results")
console = Console()


def load_per_run_results(path: Path) -> List[Dict]:
    """Load per-run evaluation results.

    Args:
        path: Path to per_run.json

    Returns:
        List of result dictionaries
    """
    if not path.exists():
        console.print(f"[yellow]Warning: {path} not found[/yellow]")
        return []

    with open(path, "r") as f:
        return json.load(f)


def load_results_csv(path: Path) -> pd.DataFrame:
    """Load results CSV as pandas DataFrame.

    Args:
        path: Path to results.csv

    Returns:
        DataFrame with results
    """
    if not path.exists():
        console.print(f"[red]Error: {path} not found[/red]")
        raise FileNotFoundError(path)

    return pd.read_csv(path)


def calculate_engine_comparison(eval_results: List[Dict], results_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate comparison metrics across engines.

    Args:
        eval_results: Per-run evaluation results
        results_df: Results DataFrame with execution metadata

    Returns:
        DataFrame with engine comparison metrics
    """
    # Create DataFrame from evaluation results
    eval_df = pd.DataFrame(eval_results)

    if eval_df.empty:
        return pd.DataFrame()

    # Merge with execution metadata
    merged = eval_df.merge(
        results_df[["run_id", "prompt_tokens", "completion_tokens", "total_tokens"]],
        on="run_id",
        how="left"
    )

    # Group by engine
    engine_stats = []

    for engine in merged["engine"].unique():
        engine_data = merged[merged["engine"] == engine]

        # Extract metrics
        metrics_list = [r["metrics"] for r in eval_results if r["engine"] == engine]

        if not metrics_list:
            continue

        # Aggregate metrics
        total_claims = sum(m["total_claims"] for m in metrics_list)
        hit_rate_avg = np.mean([m["hit_rate"] for m in metrics_list])
        contradiction_rate_avg = np.mean([m["contradiction_rate"] for m in metrics_list])
        unsupported_rate_avg = np.mean([m["unsupported_rate"] for m in metrics_list])
        overclaim_rate_avg = np.mean([m["overclaim_rate"] for m in metrics_list])

        # Token stats
        avg_prompt_tokens = engine_data["prompt_tokens"].mean()
        avg_completion_tokens = engine_data["completion_tokens"].mean()
        avg_total_tokens = engine_data["total_tokens"].mean()

        # Error counts
        numeric_errors = sum(r["numeric_error_count"] for r in eval_results if r["engine"] == engine)
        unit_errors = sum(r["unit_error_count"] for r in eval_results if r["engine"] == engine)

        engine_stats.append({
            "engine": engine,
            "runs": len(engine_data),
            "total_claims": total_claims,
            "hit_rate": hit_rate_avg,
            "contradiction_rate": contradiction_rate_avg,
            "unsupported_rate": unsupported_rate_avg,
            "overclaim_rate": overclaim_rate_avg,
            "numeric_errors": numeric_errors,
            "unit_errors": unit_errors,
            "avg_prompt_tokens": avg_prompt_tokens,
            "avg_completion_tokens": avg_completion_tokens,
            "avg_total_tokens": avg_total_tokens,
        })

    return pd.DataFrame(engine_stats)


def calculate_drift_analysis(eval_results: List[Dict]) -> pd.DataFrame:
    """Analyze consistency across repetitions (days).

    Args:
        eval_results: Per-run evaluation results

    Returns:
        DataFrame with drift analysis
    """
    eval_df = pd.DataFrame(eval_results)

    if eval_df.empty or "temperature" not in eval_df.columns:
        return pd.DataFrame()

    # Group by engine, product, material, temperature
    drift_stats = []

    groupby_cols = ["engine", "product_id", "material_type", "temperature"]
    for group_key, group_data in eval_df.groupby(groupby_cols):
        metrics_list = group_data["metrics"].tolist()

        if len(metrics_list) < 2:
            continue

        # Extract rates across repetitions
        hit_rates = [m["hit_rate"] for m in metrics_list]
        overclaim_rates = [m["overclaim_rate"] for m in metrics_list]

        drift_stats.append({
            "engine": group_key[0],
            "product_id": group_key[1],
            "material_type": group_key[2],
            "temperature": group_key[3],
            "repetitions": len(metrics_list),
            "hit_rate_mean": np.mean(hit_rates),
            "hit_rate_std": np.std(hit_rates),
            "hit_rate_cv": np.std(hit_rates) / np.mean(hit_rates) if np.mean(hit_rates) > 0 else 0,
            "overclaim_rate_mean": np.mean(overclaim_rates),
            "overclaim_rate_std": np.std(overclaim_rates),
        })

    return pd.DataFrame(drift_stats)


def calculate_temperature_effects(eval_results: List[Dict]) -> pd.DataFrame:
    """Analyze temperature effects on metrics.

    Args:
        eval_results: Per-run evaluation results

    Returns:
        DataFrame with temperature analysis
    """
    eval_df = pd.DataFrame(eval_results)

    if eval_df.empty or "temperature" not in eval_df.columns:
        return pd.DataFrame()

    temp_stats = []

    for (engine, product_id, temp), group_data in eval_df.groupby(["engine", "product_id", "temperature"]):
        metrics_list = group_data["metrics"].tolist()

        hit_rate_avg = np.mean([m["hit_rate"] for m in metrics_list])
        overclaim_rate_avg = np.mean([m["overclaim_rate"] for m in metrics_list])

        temp_stats.append({
            "engine": engine,
            "product_id": product_id,
            "temperature": temp,
            "runs": len(metrics_list),
            "hit_rate": hit_rate_avg,
            "overclaim_rate": overclaim_rate_avg,
        })

    return pd.DataFrame(temp_stats)


def calculate_product_breakdown(eval_results: List[Dict]) -> pd.DataFrame:
    """Calculate metrics by product and material type.

    Args:
        eval_results: Per-run evaluation results

    Returns:
        DataFrame with product × material breakdown
    """
    eval_df = pd.DataFrame(eval_results)

    if eval_df.empty:
        return pd.DataFrame()

    product_stats = []

    for (engine, product_id, material), group_data in eval_df.groupby(["engine", "product_id", "material_type"]):
        metrics_list = group_data["metrics"].tolist()

        hit_rate_avg = np.mean([m["hit_rate"] for m in metrics_list])
        overclaim_rate_avg = np.mean([m["overclaim_rate"] for m in metrics_list])

        product_stats.append({
            "engine": engine,
            "product_id": product_id,
            "material_type": material,
            "runs": len(metrics_list),
            "hit_rate": hit_rate_avg,
            "overclaim_rate": overclaim_rate_avg,
        })

    return pd.DataFrame(product_stats)


@app.command()
def main(
    results_csv: str = typer.Option(
        "results/results.csv",
        help="Path to results CSV"
    ),
    per_run_json: str = typer.Option(
        "analysis/per_run.json",
        help="Path to per-run evaluation JSON"
    ),
    output_dir: str = typer.Option(
        "analysis",
        help="Output directory for reports"
    ),
    generate_plots: bool = typer.Option(
        False,
        "--plots",
        help="Generate matplotlib visualizations"
    ),
) -> None:
    """Generate comprehensive analytics reports.

    Outputs:
    - analysis/engine_comparison.csv
    - analysis/drift_analysis.csv
    - analysis/temperature_effects.csv
    - analysis/product_breakdown.csv
    - (optional) analysis/plots/*.png
    """
    console.print("\n[bold]Generating Analytics Reports[/bold]\n")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Load data
    console.print("[cyan]Loading data...[/cyan]")
    results_df = load_results_csv(Path(results_csv))
    eval_results = load_per_run_results(Path(per_run_json))

    if not eval_results:
        console.print("[yellow]No evaluation results found. Run 'python -m analysis.evaluate' first.[/yellow]")
        return

    console.print(f"[green]✓[/green] Loaded {len(results_df)} runs, {len(eval_results)} evaluations\n")

    # 1. Engine Comparison
    console.print("[cyan]Calculating engine comparison...[/cyan]")
    engine_comp = calculate_engine_comparison(eval_results, results_df)
    if not engine_comp.empty:
        engine_comp.to_csv(output_path / "engine_comparison.csv", index=False)
        console.print(f"[green]✓[/green] Saved engine_comparison.csv")

        # Display table
        table = Table(title="Engine Comparison")
        table.add_column("Engine", style="cyan")
        table.add_column("Runs", style="bold")
        table.add_column("Hit Rate", style="green")
        table.add_column("Overclaim", style="red")
        table.add_column("Avg Tokens", style="yellow")

        for _, row in engine_comp.iterrows():
            table.add_row(
                row["engine"],
                str(row["runs"]),
                f"{row['hit_rate']:.2%}",
                f"{row['overclaim_rate']:.2%}",
                f"{row['avg_total_tokens']:.0f}",
            )

        console.print(table)
        console.print()

    # 2. Drift Analysis
    console.print("[cyan]Analyzing drift across repetitions...[/cyan]")
    drift_df = calculate_drift_analysis(eval_results)
    if not drift_df.empty:
        drift_df.to_csv(output_path / "drift_analysis.csv", index=False)
        console.print(f"[green]✓[/green] Saved drift_analysis.csv\n")

    # 3. Temperature Effects
    console.print("[cyan]Analyzing temperature effects...[/cyan]")
    temp_df = calculate_temperature_effects(eval_results)
    if not temp_df.empty:
        temp_df.to_csv(output_path / "temperature_effects.csv", index=False)
        console.print(f"[green]✓[/green] Saved temperature_effects.csv\n")

    # 4. Product Breakdown
    console.print("[cyan]Calculating product × material breakdown...[/cyan]")
    product_df = calculate_product_breakdown(eval_results)
    if not product_df.empty:
        product_df.to_csv(output_path / "product_breakdown.csv", index=False)
        console.print(f"[green]✓[/green] Saved product_breakdown.csv\n")

    # 5. Generate plots (optional)
    if generate_plots:
        console.print("[cyan]Generating visualizations...[/cyan]")
        plots_dir = output_path / "plots"
        plots_dir.mkdir(exist_ok=True)

        try:
            import matplotlib
            matplotlib.use('Agg')  # Non-interactive backend
            import matplotlib.pyplot as plt

            # Plot 1: Engine comparison bar chart
            if not engine_comp.empty:
                fig, ax = plt.subplots(figsize=(10, 6))
                x = np.arange(len(engine_comp))
                width = 0.35

                ax.bar(x - width/2, engine_comp["hit_rate"], width, label="Hit Rate", color="green", alpha=0.7)
                ax.bar(x + width/2, engine_comp["overclaim_rate"], width, label="Overclaim Rate", color="red", alpha=0.7)

                ax.set_xlabel("Engine")
                ax.set_ylabel("Rate")
                ax.set_title("Engine Performance Comparison")
                ax.set_xticks(x)
                ax.set_xticklabels(engine_comp["engine"])
                ax.legend()
                ax.grid(True, alpha=0.3)

                plt.tight_layout()
                plt.savefig(plots_dir / "engine_comparison.png", dpi=150)
                plt.close()

                console.print(f"[green]✓[/green] Generated engine_comparison.png")

            # Plot 2: Temperature effects
            if not temp_df.empty:
                fig, axes = plt.subplots(1, 2, figsize=(14, 6))

                for engine in temp_df["engine"].unique():
                    engine_data = temp_df[temp_df["engine"] == engine]

                    axes[0].plot(
                        engine_data["temperature"],
                        engine_data["hit_rate"],
                        marker="o",
                        label=engine
                    )

                    axes[1].plot(
                        engine_data["temperature"],
                        engine_data["overclaim_rate"],
                        marker="o",
                        label=engine
                    )

                axes[0].set_title("Hit Rate vs Temperature")
                axes[0].set_xlabel("Temperature")
                axes[0].set_ylabel("Hit Rate")
                axes[0].legend()
                axes[0].grid(True, alpha=0.3)

                axes[1].set_title("Overclaim Rate vs Temperature")
                axes[1].set_xlabel("Temperature")
                axes[1].set_ylabel("Overclaim Rate")
                axes[1].legend()
                axes[1].grid(True, alpha=0.3)

                plt.tight_layout()
                plt.savefig(plots_dir / "temperature_effects.png", dpi=150)
                plt.close()

                console.print(f"[green]✓[/green] Generated temperature_effects.png")

        except ImportError as e:
            console.print(f"[yellow]Warning: Could not generate plots: {e}[/yellow]")

    console.print("\n[bold green]✓ Analytics reports complete[/bold green]")
    console.print(f"Reports saved to: {output_path}\n")


if __name__ == "__main__":
    app()
