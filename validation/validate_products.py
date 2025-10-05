"""Product YAML validation script."""

import re
from pathlib import Path
from typing import List, Tuple

import yaml
from pydantic import ValidationError
from rich.console import Console
from rich.table import Table

from runner.schema import Product

console = Console()


def has_units(spec: str) -> bool:
    """Check if a spec contains unit notation (parentheses with units).

    Args:
        spec: Specification string

    Returns:
        True if units are present in parentheses
    """
    # Look for patterns like (mg), (GB), (Hz), (in), (count), etc.
    # Also accepts compound units like (3 mg per serving)
    unit_pattern = r'\([^)]*[a-zA-Z]+[^)]*\)'
    return bool(re.search(unit_pattern, spec))


def validate_product_file(product_path: Path) -> Tuple[bool, List[str]]:
    """Validate a single product YAML file.

    Args:
        product_path: Path to product YAML file

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    try:
        # Load YAML
        with open(product_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        # Validate with Pydantic schema
        product = Product(**data)

        # Check that all specs contain units
        specs_without_units = [
            spec for spec in product.specs if not has_units(spec)
        ]

        if specs_without_units:
            errors.append(
                f"Specs missing unit notation: {specs_without_units}"
            )

        return (len(errors) == 0, errors)

    except FileNotFoundError:
        errors.append(f"File not found: {product_path}")
        return (False, errors)

    except yaml.YAMLError as e:
        errors.append(f"YAML parse error: {e}")
        return (False, errors)

    except ValidationError as e:
        errors.append(f"Schema validation failed: {e}")
        return (False, errors)

    except Exception as e:
        errors.append(f"Unexpected error: {e}")
        return (False, errors)


def main() -> None:
    """Validate all product YAML files in the products directory."""
    products_dir = Path("products")

    if not products_dir.exists():
        console.print(f"[red]Error: Products directory not found: {products_dir}[/red]")
        return

    product_files = sorted(products_dir.glob("*.yaml"))

    if not product_files:
        console.print(f"[yellow]Warning: No YAML files found in {products_dir}[/yellow]")
        return

    # Validate each product
    results = []
    for product_file in product_files:
        is_valid, errors = validate_product_file(product_file)
        results.append((product_file.name, is_valid, errors))

    # Display results in table
    table = Table(title="Product Validation Results")
    table.add_column("Product File", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Errors", style="red")

    for filename, is_valid, errors in results:
        status = "[green]✓ VALID[/green]" if is_valid else "[red]✗ INVALID[/red]"
        error_text = "\n".join(errors) if errors else ""
        table.add_row(filename, status, error_text)

    console.print(table)

    # Summary
    valid_count = sum(1 for _, is_valid, _ in results if is_valid)
    total_count = len(results)

    if valid_count == total_count:
        console.print(f"\n[green]✓ {valid_count}/{total_count} products valid[/green]")
    else:
        console.print(f"\n[red]✗ {valid_count}/{total_count} products valid[/red]")


if __name__ == "__main__":
    main()
