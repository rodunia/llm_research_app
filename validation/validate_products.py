"""Product YAML validation script."""

import sys
from pathlib import Path
from typing import List, Tuple

import yaml
from pydantic import ValidationError

from runner.schema import Product, has_unit


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

        # Validate with Pydantic schema (includes spec unit validation)
        Product(**data)

        return (True, [])

    except FileNotFoundError:
        errors.append(f"File not found: {product_path}")
        return (False, errors)

    except yaml.YAMLError as e:
        errors.append(f"YAML parse error: {e}")
        return (False, errors)

    except ValidationError as e:
        # Extract readable error messages
        for error in e.errors():
            field = ".".join(str(loc) for loc in error["loc"])
            msg = error["msg"]
            errors.append(f"{field}: {msg}")
        return (False, errors)

    except Exception as e:
        errors.append(f"Unexpected error: {e}")
        return (False, errors)


def main() -> None:
    """Validate all product YAML files in the products directory."""
    products_dir = Path("products")

    if not products_dir.exists():
        print(f"Error: Products directory not found: {products_dir}")
        sys.exit(1)

    product_files = sorted(products_dir.glob("*.yaml"))

    if not product_files:
        print(f"Warning: No YAML files found in {products_dir}")
        sys.exit(0)

    # Validate each product
    results = []
    for product_file in product_files:
        is_valid, errors = validate_product_file(product_file)
        results.append((product_file.name, is_valid, errors))

    # Display results
    has_errors = False
    for filename, is_valid, errors in results:
        if is_valid:
            print(f"✓ {filename}")
        else:
            has_errors = True
            print(f"✗ {filename}")
            for error in errors:
                print(f"  - {error}")

    # Summary
    valid_count = sum(1 for _, is_valid, _ in results if is_valid)
    total_count = len(results)

    print(f"\n{valid_count}/{total_count} products valid")

    # Exit with error code if any validation failed
    if has_errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
