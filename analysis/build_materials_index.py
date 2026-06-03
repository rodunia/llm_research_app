"""
Materials Index Builder

Scans outputs/ directory and experiments.csv to build a complete index of all
generated marketing materials for compliance analysis.

Output: results/materials_index.csv

Columns:
- run_id
- product_id
- product_name
- product_type
- regulatory_domain
- material_type
- generator_model
- generator_engine
- temperature
- output_path
- product_yaml_path
- created_at (completed_at from experiments.csv)
- status (pending/completed/failed)
- finish_reason
- completion_tokens
- prompt_tokens

Usage:
    python analysis/build_materials_index.py
    python analysis/build_materials_index.py --filter-status completed
    python analysis/build_materials_index.py --output results/materials_index_completed.csv
"""

import csv
import sys
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
import yaml

app = typer.Typer()
console = Console()


def load_product_yaml(product_id: str) -> Dict:
    """Load product YAML to extract metadata."""
    yaml_path = Path(f"products/{product_id}.yaml")
    if not yaml_path.exists():
        return {
            "name": f"Unknown ({product_id})",
            "category_focus": "Unknown",
            "regulatory_classification": "Unknown"
        }

    with open(yaml_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def scan_outputs_directory() -> Dict[str, bool]:
    """Scan outputs/ directory and return set of run_ids with output files."""
    outputs_dir = Path("outputs")
    output_files = {}

    if not outputs_dir.exists():
        console.print("[yellow]Warning: outputs/ directory not found[/yellow]")
        return output_files

    for output_file in outputs_dir.glob("*.txt"):
        run_id = output_file.stem
        if len(run_id) == 40:  # SHA-1 hash length
            output_files[run_id] = True

    return output_files


def build_materials_index(
    experiments_csv: Path,
    filter_status: Optional[str] = None,
    require_output_file: bool = True
) -> List[Dict]:
    """
    Build materials index from experiments.csv.

    Args:
        experiments_csv: Path to experiments.csv
        filter_status: Only include runs with this status (completed/pending/failed)
        require_output_file: Only include runs that have output files

    Returns:
        List of material records
    """
    if not experiments_csv.exists():
        console.print(f"[red]Error: {experiments_csv} not found[/red]")
        sys.exit(1)

    # Scan output files
    output_files = scan_outputs_directory()
    console.print(f"Found {len(output_files)} output files in outputs/")

    materials = []
    skipped_no_output = 0
    skipped_status = 0

    with open(experiments_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row in reader:
            run_id = row.get('run_id')
            status = row.get('status', 'unknown')

            # Filter by status
            if filter_status and status != filter_status:
                skipped_status += 1
                continue

            # Check output file exists
            if require_output_file and run_id not in output_files:
                skipped_no_output += 1
                continue

            product_id = row.get('product_id')

            # Load product metadata
            product_yaml = load_product_yaml(product_id)

            material = {
                'run_id': run_id,
                'product_id': product_id,
                'product_name': product_yaml.get('name', f'Unknown ({product_id})'),
                'product_type': product_yaml.get('category_focus', 'Unknown'),
                'regulatory_domain': product_yaml.get('regulatory_classification', 'Unknown'),
                'material_type': row.get('material_type', ''),
                'generator_model': row.get('model', ''),
                'generator_engine': row.get('engine', ''),
                'temperature': row.get('temperature', ''),
                'output_path': f"outputs/{run_id}.txt",
                'product_yaml_path': f"products/{product_id}.yaml",
                'created_at': row.get('completed_at', ''),
                'status': status,
                'finish_reason': row.get('finish_reason', ''),
                'completion_tokens': row.get('completion_tokens', '0'),
                'prompt_tokens': row.get('prompt_tokens', '0'),
            }

            materials.append(material)

    console.print(f"Indexed {len(materials)} materials")
    if skipped_no_output > 0:
        console.print(f"Skipped {skipped_no_output} runs without output files")
    if skipped_status > 0:
        console.print(f"Skipped {skipped_status} runs due to status filter")

    return materials


def write_materials_index(materials: List[Dict], output_path: Path):
    """Write materials index to CSV."""
    if not materials:
        console.print("[yellow]No materials to write[/yellow]")
        return

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        'run_id',
        'product_id',
        'product_name',
        'product_type',
        'regulatory_domain',
        'material_type',
        'generator_model',
        'generator_engine',
        'temperature',
        'output_path',
        'product_yaml_path',
        'created_at',
        'status',
        'finish_reason',
        'completion_tokens',
        'prompt_tokens'
    ]

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(materials)

    console.print(f"\n[green]✓ Wrote materials index to {output_path}[/green]")


@app.command()
def build(
    experiments_csv: str = typer.Option(
        "results/experiments.csv",
        "--experiments",
        "-e",
        help="Path to experiments.csv"
    ),
    output: str = typer.Option(
        "results/materials_index.csv",
        "--output",
        "-o",
        help="Output CSV path"
    ),
    filter_status: Optional[str] = typer.Option(
        None,
        "--filter-status",
        "-s",
        help="Only include runs with this status (completed/pending/failed)"
    ),
    require_output: bool = typer.Option(
        True,
        "--require-output/--no-require-output",
        help="Only include runs that have output files"
    )
):
    """Build materials index from experiments.csv and outputs/ directory."""
    console.print("\n[bold]Building Materials Index[/bold]\n")

    experiments_path = Path(experiments_csv)
    output_path = Path(output)

    materials = build_materials_index(
        experiments_path,
        filter_status=filter_status,
        require_output_file=require_output
    )

    if not materials:
        console.print("[red]No materials found matching criteria[/red]\n")
        sys.exit(1)

    write_materials_index(materials, output_path)

    # Print summary statistics
    console.print("\n[bold]Summary Statistics:[/bold]")

    # By product
    by_product = {}
    for m in materials:
        product = m['product_id']
        by_product[product] = by_product.get(product, 0) + 1

    console.print("\n[cyan]By Product:[/cyan]")
    for product, count in sorted(by_product.items()):
        console.print(f"  {product}: {count}")

    # By material type
    by_material = {}
    for m in materials:
        material_type = m['material_type']
        by_material[material_type] = by_material.get(material_type, 0) + 1

    console.print("\n[cyan]By Material Type:[/cyan]")
    for material_type, count in sorted(by_material.items()):
        console.print(f"  {material_type}: {count}")

    # By engine
    by_engine = {}
    for m in materials:
        engine = m['generator_engine']
        by_engine[engine] = by_engine.get(engine, 0) + 1

    console.print("\n[cyan]By Generator Engine:[/cyan]")
    for engine, count in sorted(by_engine.items()):
        console.print(f"  {engine}: {count}")

    # By status
    by_status = {}
    for m in materials:
        status = m['status']
        by_status[status] = by_status.get(status, 0) + 1

    console.print("\n[cyan]By Status:[/cyan]")
    for status, count in sorted(by_status.items()):
        console.print(f"  {status}: {count}")

    console.print(f"\n[bold green]Total materials indexed: {len(materials)}[/bold green]\n")


@app.command()
def validate_index(
    index_csv: str = typer.Option(
        "results/materials_index.csv",
        "--index",
        "-i",
        help="Path to materials index CSV"
    )
):
    """Validate that all files in materials index exist."""
    console.print("\n[bold]Validating Materials Index[/bold]\n")

    index_path = Path(index_csv)
    if not index_path.exists():
        console.print(f"[red]Error: {index_path} not found[/red]")
        sys.exit(1)

    missing_outputs = []
    missing_yamls = []

    with open(index_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        total = 0

        for row in reader:
            total += 1
            output_path = Path(row['output_path'])
            yaml_path = Path(row['product_yaml_path'])

            if not output_path.exists():
                missing_outputs.append(row['run_id'])

            if not yaml_path.exists():
                missing_yamls.append(row['product_id'])

    console.print(f"Validated {total} materials")

    if missing_outputs:
        console.print(f"\n[red]Missing output files: {len(missing_outputs)}[/red]")
        for run_id in missing_outputs[:5]:
            console.print(f"  • {run_id}")
        if len(missing_outputs) > 5:
            console.print(f"  ... and {len(missing_outputs) - 5} more")

    if missing_yamls:
        console.print(f"\n[red]Missing product YAMLs: {len(set(missing_yamls))}[/red]")
        for product_id in set(missing_yamls):
            console.print(f"  • {product_id}")

    if missing_outputs or missing_yamls:
        console.print("\n[red]Validation failed![/red]\n")
        sys.exit(1)
    else:
        console.print("\n[green]✓ All files exist![/green]\n")
        sys.exit(0)


if __name__ == "__main__":
    app()
