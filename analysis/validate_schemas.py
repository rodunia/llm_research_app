"""
Schema Validation for Compliance Analysis Pipeline

Validates:
- Product YAML files against product_context schema
- GPT-4o JSON outputs against gpt4o_compliance_output schema
- RoBERTa JSON outputs against roberta_validation_output schema
- Claude JSON outputs against claude_review_output schema
- Human queue entries against human_queue schema

Usage:
    python analysis/validate_schemas.py --type product --file products/supplement_melatonin.yaml
    python analysis/validate_schemas.py --type gpt4o --file results/gpt4o_compliance/abc123.json
    python analysis/validate_schemas.py --validate-all
"""

import json
import sys
import yaml
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import jsonschema
from jsonschema import validate, ValidationError, Draft7Validator
import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer()
console = Console()

# Schema file paths
SCHEMA_DIR = Path("analysis/schemas")
SCHEMAS = {
    "material_input": SCHEMA_DIR / "material_input.schema.json",
    "product": SCHEMA_DIR / "product_context.schema.json",
    "gpt4o": SCHEMA_DIR / "gpt4o_compliance_output.schema.json",
    "roberta": SCHEMA_DIR / "roberta_validation_output.schema.json",
    "claude": SCHEMA_DIR / "claude_review_output.schema.json",
    "human_queue": SCHEMA_DIR / "human_queue.schema.json",
}


def load_schema(schema_type: str) -> dict:
    """Load JSON schema file."""
    schema_path = SCHEMAS.get(schema_type)
    if not schema_path or not schema_path.exists():
        console.print(f"[red]Schema not found: {schema_type}[/red]")
        raise FileNotFoundError(f"Schema file not found: {schema_path}")

    with open(schema_path, 'r') as f:
        return json.load(f)


def load_data_file(file_path: Path) -> dict:
    """Load JSON or YAML data file."""
    if not file_path.exists():
        raise FileNotFoundError(f"Data file not found: {file_path}")

    if file_path.suffix in ['.yaml', '.yml']:
        with open(file_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    elif file_path.suffix == '.json':
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        raise ValueError(f"Unsupported file format: {file_path.suffix}")


def validate_data(data: dict, schema: dict, file_path: Optional[Path] = None) -> Tuple[bool, List[str]]:
    """
    Validate data against schema.

    Returns:
        (is_valid, errors_list)
    """
    validator = Draft7Validator(schema)
    errors = []

    for error in validator.iter_errors(data):
        # Build error path
        path = " -> ".join(str(p) for p in error.path) if error.path else "root"
        error_msg = f"{path}: {error.message}"
        errors.append(error_msg)

    is_valid = len(errors) == 0

    return is_valid, errors


def validate_file(file_path: Path, schema_type: str) -> Tuple[bool, List[str]]:
    """Validate a single file against schema."""
    try:
        data = load_data_file(file_path)
        schema = load_schema(schema_type)
        return validate_data(data, schema, file_path)
    except Exception as e:
        return False, [f"Error loading file: {str(e)}"]


@app.command()
def validate(
    file_path: str = typer.Option(..., "--file", "-f", help="Path to file to validate"),
    schema_type: str = typer.Option(..., "--type", "-t", help="Schema type (product, gpt4o, roberta, claude, human_queue)")
):
    """Validate a single file against a schema."""
    path = Path(file_path)

    console.print(f"\n[bold]Validating {path.name}[/bold]")
    console.print(f"Schema: {schema_type}\n")

    is_valid, errors = validate_file(path, schema_type)

    if is_valid:
        console.print("[green]✓ Validation passed![/green]\n")
        sys.exit(0)
    else:
        console.print("[red]✗ Validation failed![/red]\n")
        console.print("[bold]Errors:[/bold]")
        for error in errors:
            console.print(f"  • {error}")
        console.print()
        sys.exit(1)


@app.command()
def validate_all(
    products: bool = typer.Option(True, help="Validate product YAML files"),
    gpt4o: bool = typer.Option(False, help="Validate GPT-4o outputs"),
    roberta: bool = typer.Option(False, help="Validate RoBERTa outputs"),
    claude: bool = typer.Option(False, help="Validate Claude outputs"),
    fail_fast: bool = typer.Option(False, help="Exit on first validation error")
):
    """Validate all files of specified types."""
    console.print("\n[bold]Running batch validation[/bold]\n")

    results = []

    # Validate product YAMLs
    if products:
        console.print("[bold cyan]Validating product YAML files...[/bold cyan]")
        product_dir = Path("products")
        if product_dir.exists():
            for yaml_file in product_dir.glob("*.yaml"):
                is_valid, errors = validate_file(yaml_file, "product")
                results.append(("product", yaml_file.name, is_valid, len(errors)))

                if not is_valid:
                    console.print(f"  [red]✗ {yaml_file.name}[/red]")
                    for error in errors[:3]:  # Show first 3 errors
                        console.print(f"    • {error}")
                    if len(errors) > 3:
                        console.print(f"    ... and {len(errors) - 3} more errors")

                    if fail_fast:
                        console.print("\n[red]Stopping due to --fail-fast[/red]\n")
                        sys.exit(1)
                else:
                    console.print(f"  [green]✓ {yaml_file.name}[/green]")
        console.print()

    # Validate GPT-4o outputs
    if gpt4o:
        console.print("[bold cyan]Validating GPT-4o outputs...[/bold cyan]")
        gpt4o_dir = Path("results/gpt4o_compliance")
        if gpt4o_dir.exists():
            for json_file in gpt4o_dir.glob("*.json"):
                is_valid, errors = validate_file(json_file, "gpt4o")
                results.append(("gpt4o", json_file.name, is_valid, len(errors)))

                if not is_valid:
                    console.print(f"  [red]✗ {json_file.name}[/red]")
                    for error in errors[:3]:
                        console.print(f"    • {error}")
                    if len(errors) > 3:
                        console.print(f"    ... and {len(errors) - 3} more errors")

                    if fail_fast:
                        console.print("\n[red]Stopping due to --fail-fast[/red]\n")
                        sys.exit(1)
                else:
                    console.print(f"  [green]✓ {json_file.name}[/green]")
        console.print()

    # Validate RoBERTa outputs
    if roberta:
        console.print("[bold cyan]Validating RoBERTa outputs...[/bold cyan]")
        roberta_dir = Path("results/roberta_validation")
        if roberta_dir.exists():
            for json_file in roberta_dir.glob("*.json"):
                is_valid, errors = validate_file(json_file, "roberta")
                results.append(("roberta", json_file.name, is_valid, len(errors)))

                if not is_valid:
                    console.print(f"  [red]✗ {json_file.name}[/red]")
                    for error in errors[:3]:
                        console.print(f"    • {error}")
                    if len(errors) > 3:
                        console.print(f"    ... and {len(errors) - 3} more errors")

                    if fail_fast:
                        console.print("\n[red]Stopping due to --fail-fast[/red]\n")
                        sys.exit(1)
                else:
                    console.print(f"  [green]✓ {json_file.name}[/green]")
        console.print()

    # Validate Claude outputs
    if claude:
        console.print("[bold cyan]Validating Claude outputs...[/bold cyan]")
        claude_dir = Path("results/claude_review")
        if claude_dir.exists():
            for json_file in claude_dir.glob("*.json"):
                is_valid, errors = validate_file(json_file, "claude")
                results.append(("claude", json_file.name, is_valid, len(errors)))

                if not is_valid:
                    console.print(f"  [red]✗ {json_file.name}[/red]")
                    for error in errors[:3]:
                        console.print(f"    • {error}")
                    if len(errors) > 3:
                        console.print(f"    ... and {len(errors) - 3} more errors")

                    if fail_fast:
                        console.print("\n[red]Stopping due to --fail-fast[/red]\n")
                        sys.exit(1)
                else:
                    console.print(f"  [green]✓ {json_file.name}[/green]")
        console.print()

    # Summary table
    if results:
        table = Table(title="Validation Summary")
        table.add_column("Type", style="cyan")
        table.add_column("Total", justify="right")
        table.add_column("Valid", justify="right", style="green")
        table.add_column("Invalid", justify="right", style="red")

        # Group by type
        by_type = {}
        for schema_type, filename, is_valid, error_count in results:
            if schema_type not in by_type:
                by_type[schema_type] = {"total": 0, "valid": 0, "invalid": 0}
            by_type[schema_type]["total"] += 1
            if is_valid:
                by_type[schema_type]["valid"] += 1
            else:
                by_type[schema_type]["invalid"] += 1

        for schema_type, counts in by_type.items():
            table.add_row(
                schema_type,
                str(counts["total"]),
                str(counts["valid"]),
                str(counts["invalid"])
            )

        console.print(table)
        console.print()

        # Exit code
        total_invalid = sum(c["invalid"] for c in by_type.values())
        if total_invalid > 0:
            console.print(f"[red]Validation failed: {total_invalid} invalid file(s)[/red]\n")
            sys.exit(1)
        else:
            console.print("[green]All validations passed![/green]\n")
            sys.exit(0)
    else:
        console.print("[yellow]No files found to validate[/yellow]\n")
        sys.exit(0)


@app.command()
def check_required_fields(
    file_path: str = typer.Option(..., "--file", "-f", help="Path to JSON file"),
    schema_type: str = typer.Option(..., "--type", "-t", help="Schema type")
):
    """Check which required fields are missing from a file."""
    path = Path(file_path)
    data = load_data_file(path)
    schema = load_schema(schema_type)

    required_fields = schema.get("required", [])

    console.print(f"\n[bold]Required fields check for {path.name}[/bold]\n")

    missing = []
    present = []

    for field in required_fields:
        if field in data:
            present.append(field)
        else:
            missing.append(field)

    if present:
        console.print("[bold green]Present fields:[/bold green]")
        for field in present:
            console.print(f"  ✓ {field}")
        console.print()

    if missing:
        console.print("[bold red]Missing fields:[/bold red]")
        for field in missing:
            console.print(f"  ✗ {field}")
        console.print()
        sys.exit(1)
    else:
        console.print("[green]All required fields present![/green]\n")
        sys.exit(0)


if __name__ == "__main__":
    app()
