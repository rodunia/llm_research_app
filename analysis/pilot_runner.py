"""
Pilot Runner - GPT-4o Compliance Analysis

Runs GPT-4o compliance analysis on a pilot sample (~20 materials) before full dataset.

Stratified sampling:
- 5-7 melatonin materials
- 5-7 crypto materials
- 5-7 smartphone materials
- Mix of engines (openai, google, mistral)
- Mix of temperatures (0.2, 0.6, 1.0)
- Mix of material types (faq, digital_ad, blog_post, social_posts)

Output: results/pilot/gpt4o_compliance/{run_id}.json

Usage:
    python analysis/pilot_runner.py --sample-size 20
    python analysis/pilot_runner.py --sample-size 20 --dry-run
    python analysis/pilot_runner.py --validate-outputs
"""

import json
import csv
import sys
from pathlib import Path
from typing import List, Dict, Optional
import random
from datetime import datetime
import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table

# Import GPT-4o judge
from analysis.gpt4o_grey_area_judge import judge_marketing_material, load_product_yaml

app = typer.Typer()
console = Console()

# Output directory
PILOT_OUTPUT_DIR = Path("results/pilot/gpt4o_compliance")


def load_materials_index(index_path: Path) -> List[Dict]:
    """Load materials index CSV."""
    if not index_path.exists():
        console.print(f"[red]Error: Materials index not found: {index_path}[/red]")
        console.print("[yellow]Run: python analysis/build_materials_index.py[/yellow]")
        sys.exit(1)

    materials = []
    with open(index_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        materials = list(reader)

    return materials


def stratified_sample_materials(
    materials: List[Dict],
    sample_size: int = 20,
    seed: int = 42
) -> List[Dict]:
    """
    Stratified sampling of materials by product, engine, temperature, material_type.

    Targets:
    - ~7 per product (melatonin, crypto, smartphone)
    - Mix of engines
    - Mix of temperatures
    - Mix of material types
    """
    random.seed(seed)

    # Group by product
    by_product = {}
    for m in materials:
        product = m['product_id']
        if product not in by_product:
            by_product[product] = []
        by_product[product].append(m)

    console.print(f"\nAvailable materials by product:")
    for product, mats in by_product.items():
        console.print(f"  {product}: {len(mats)}")

    # Sample evenly from each product
    samples_per_product = sample_size // len(by_product)
    remainder = sample_size % len(by_product)

    sampled = []

    for i, (product, mats) in enumerate(sorted(by_product.items())):
        # First product gets remainder
        n = samples_per_product + (remainder if i == 0 else 0)
        n = min(n, len(mats))  # Can't sample more than available

        # Shuffle for randomness within product
        random.shuffle(mats)
        product_sample = mats[:n]

        console.print(f"  Sampling {n} from {product}")
        sampled.extend(product_sample)

    console.print(f"\nTotal sampled: {len(sampled)}")

    return sampled


def run_gpt4o_analysis(material: Dict, output_dir: Path) -> Dict:
    """
    Run GPT-4o compliance analysis on a single material.

    Returns:
        Dict with 'success', 'output_path', 'error' keys
    """
    run_id = material['run_id']
    product_id = material['product_id']
    output_path_str = material['output_path']

    # Read material text
    output_file = Path(output_path_str)
    if not output_file.exists():
        return {
            'success': False,
            'run_id': run_id,
            'error': f"Output file not found: {output_path_str}"
        }

    with open(output_file, 'r', encoding='utf-8') as f:
        material_text = f.read()

    # Run GPT-4o judge
    try:
        result = judge_marketing_material(
            material_text=material_text,
            product_id=product_id,
            material_id=run_id
        )

        # Save result
        output_dir.mkdir(parents=True, exist_ok=True)
        result_path = output_dir / f"{run_id}.json"

        with open(result_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2)

        return {
            'success': True,
            'run_id': run_id,
            'output_path': str(result_path),
            'overall_status': result.get('overall_status'),
            'finding_count': result.get('finding_count', 0),
            'overall_severity': result.get('overall_severity'),
            'extracted_claims_count': len(result.get('extracted_claims', []))
        }

    except Exception as e:
        return {
            'success': False,
            'run_id': run_id,
            'error': str(e)
        }


@app.command()
def run(
    sample_size: int = typer.Option(20, "--sample-size", "-n", help="Number of materials to sample"),
    index_path: str = typer.Option(
        "results/materials_index.csv",
        "--index",
        "-i",
        help="Path to materials index"
    ),
    output_dir: str = typer.Option(
        "results/pilot/gpt4o_compliance",
        "--output",
        "-o",
        help="Output directory for GPT-4o results"
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show sampling without running analysis"),
    seed: int = typer.Option(42, "--seed", help="Random seed for sampling")
):
    """Run GPT-4o pilot analysis on stratified sample of materials."""
    console.print("\n[bold]GPT-4o Pilot Runner[/bold]\n")

    # Load materials index
    materials = load_materials_index(Path(index_path))
    console.print(f"Loaded {len(materials)} materials from index")

    # Stratified sampling
    sampled = stratified_sample_materials(materials, sample_size, seed)

    # Show sample composition
    console.print("\n[bold cyan]Sample Composition:[/bold cyan]")

    by_product = {}
    by_engine = {}
    by_material_type = {}

    for m in sampled:
        product = m['product_id']
        engine = m['generator_engine']
        mat_type = m['material_type']

        by_product[product] = by_product.get(product, 0) + 1
        by_engine[engine] = by_engine.get(engine, 0) + 1
        by_material_type[mat_type] = by_material_type.get(mat_type, 0) + 1

    console.print("\n[cyan]By Product:[/cyan]")
    for product, count in sorted(by_product.items()):
        console.print(f"  {product}: {count}")

    console.print("\n[cyan]By Engine:[/cyan]")
    for engine, count in sorted(by_engine.items()):
        console.print(f"  {engine}: {count}")

    console.print("\n[cyan]By Material Type:[/cyan]")
    for mat_type, count in sorted(by_material_type.items()):
        console.print(f"  {mat_type}: {count}")

    if dry_run:
        console.print("\n[yellow]Dry run - not executing analysis[/yellow]\n")
        return

    # Run GPT-4o analysis
    console.print(f"\n[bold]Running GPT-4o analysis on {len(sampled)} materials...[/bold]\n")

    output_path = Path(output_dir)
    results = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console
    ) as progress:

        task = progress.add_task("Analyzing materials...", total=len(sampled))

        for material in sampled:
            run_id = material['run_id'][:12]
            product = material['product_id']
            progress.update(task, description=f"Analyzing {run_id} ({product})")

            result = run_gpt4o_analysis(material, output_path)
            results.append(result)

            progress.advance(task)

    # Summary
    console.print("\n[bold]Analysis Complete![/bold]\n")

    successful = [r for r in results if r.get('success')]
    failed = [r for r in results if not r.get('success')]

    console.print(f"Successful: {len(successful)}")
    console.print(f"Failed: {len(failed)}")

    if failed:
        console.print("\n[red]Failed runs:[/red]")
        for r in failed[:5]:
            console.print(f"  {r['run_id'][:12]}: {r.get('error', 'Unknown error')}")
        if len(failed) > 5:
            console.print(f"  ... and {len(failed) - 5} more")

    # Status distribution
    if successful:
        console.print("\n[cyan]Overall Status Distribution:[/cyan]")
        status_counts = {}
        for r in successful:
            status = r.get('overall_status', 'UNKNOWN')
            status_counts[status] = status_counts.get(status, 0) + 1

        for status, count in sorted(status_counts.items()):
            console.print(f"  {status}: {count}")

        # Severity distribution
        console.print("\n[cyan]Overall Severity Distribution:[/cyan]")
        severity_counts = {}
        for r in successful:
            severity = r.get('overall_severity', 'UNKNOWN')
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

        for severity, count in sorted(severity_counts.items()):
            console.print(f"  {severity}: {count}")

        # Claims extraction stats
        total_claims = sum(r.get('extracted_claims_count', 0) for r in successful)
        avg_claims = total_claims / len(successful) if successful else 0
        console.print(f"\n[cyan]Extracted Claims:[/cyan]")
        console.print(f"  Total: {total_claims}")
        console.print(f"  Average per material: {avg_claims:.1f}")

        # Findings stats
        total_findings = sum(r.get('finding_count', 0) for r in successful)
        avg_findings = total_findings / len(successful) if successful else 0
        console.print(f"\n[cyan]Compliance Findings:[/cyan]")
        console.print(f"  Total: {total_findings}")
        console.print(f"  Average per material: {avg_findings:.1f}")

    console.print(f"\n[green]✓ Results saved to {output_path}/[/green]\n")

    if failed:
        sys.exit(1)


@app.command()
def validate_outputs(
    output_dir: str = typer.Option(
        "results/pilot/gpt4o_compliance",
        "--output",
        "-o",
        help="Output directory to validate"
    )
):
    """Validate pilot outputs against schema."""
    console.print("\n[bold]Validating Pilot Outputs[/bold]\n")

    output_path = Path(output_dir)
    if not output_path.exists():
        console.print(f"[red]Output directory not found: {output_path}[/red]")
        sys.exit(1)

    json_files = list(output_path.glob("*.json"))
    console.print(f"Found {len(json_files)} JSON files")

    # Import validator
    from analysis.validate_schemas import validate_file

    valid = 0
    invalid = 0
    errors_by_file = []

    for json_file in json_files:
        is_valid, errors = validate_file(json_file, "gpt4o")

        if is_valid:
            valid += 1
        else:
            invalid += 1
            errors_by_file.append((json_file.name, errors))

    console.print(f"\nValid: {valid}")
    console.print(f"Invalid: {invalid}")

    if errors_by_file:
        console.print("\n[red]Validation errors:[/red]")
        for filename, errors in errors_by_file[:3]:
            console.print(f"\n{filename}:")
            for error in errors[:5]:
                console.print(f"  • {error}")
            if len(errors) > 5:
                console.print(f"  ... and {len(errors) - 5} more errors")

    if invalid > 0:
        console.print(f"\n[red]Validation failed: {invalid} invalid file(s)[/red]\n")
        sys.exit(1)
    else:
        console.print(f"\n[green]✓ All outputs valid![/green]\n")


if __name__ == "__main__":
    app()
