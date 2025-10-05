"""CLI for rendering and storing prompts to disk."""

import hashlib
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console

from runner.render import load_product_yaml, create_jinja_env, render_prompt

app = typer.Typer(help="Render and store prompts for LLM experiments")
console = Console()


def compute_hash16(content: str) -> str:
    """Compute a 16-character hash of content for deterministic filenames.

    Args:
        content: String content to hash

    Returns:
        First 16 characters of SHA256 hash
    """
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


def get_product_files(products_dir: Path) -> List[Path]:
    """Get all product YAML files from directory.

    Args:
        products_dir: Directory containing product YAML files

    Returns:
        Sorted list of product YAML file paths
    """
    return sorted(products_dir.glob("*.yaml"))


def get_template_files(templates_dir: Path) -> List[Path]:
    """Get all Jinja2 template files from directory.

    Args:
        templates_dir: Directory containing template files

    Returns:
        Sorted list of template file paths
    """
    return sorted(templates_dir.glob("*.j2"))


@app.command()
def main(
    products_dir: Path = typer.Option(
        Path("products"), help="Directory containing product YAML files"
    ),
    templates_dir: Path = typer.Option(
        Path("prompts"), help="Directory containing Jinja2 templates"
    ),
    out_dir: Path = typer.Option(
        Path("outputs/prompts"), help="Output directory for rendered prompts"
    ),
    trap: bool = typer.Option(
        False, "--trap", help="Enable people-pleasing trap flag"
    ),
) -> None:
    """Render all product × template combinations and store to disk.

    Generates deterministic filenames in format:
    {hash16}__{product_id}__{template_basename}.txt
    """
    # Validate input directories
    if not products_dir.exists():
        console.print(f"[red]Error: Products directory not found: {products_dir}[/red]")
        raise typer.Exit(1)

    if not templates_dir.exists():
        console.print(f"[red]Error: Templates directory not found: {templates_dir}[/red]")
        raise typer.Exit(1)

    # Create output directory
    out_dir.mkdir(parents=True, exist_ok=True)

    # Get products and templates
    product_files = get_product_files(products_dir)
    template_files = get_template_files(templates_dir)

    if not product_files:
        console.print(f"[yellow]Warning: No product YAML files found in {products_dir}[/yellow]")
        raise typer.Exit(1)

    if not template_files:
        console.print(f"[yellow]Warning: No template files found in {templates_dir}[/yellow]")
        raise typer.Exit(1)

    # Create Jinja environment
    jinja_env = create_jinja_env(templates_dir)

    # Render and store prompts
    stored_count = 0
    for product_file in product_files:
        product_data = load_product_yaml(product_file)
        product_id = product_data.get("product_id", product_file.stem)

        for template_file in template_files:
            template_name = template_file.name
            template_basename = template_file.stem

            try:
                # Render the prompt
                rendered = render_prompt(
                    product_data=product_data,
                    template_name=template_name,
                    jinja_env=jinja_env,
                    trap_flag=trap,
                )

                # Compute hash for deterministic filename
                content_hash = compute_hash16(rendered)

                # Generate filename: {hash16}__{product_id}__{template_basename}.txt
                filename = f"{content_hash}__{product_id}__{template_basename}.txt"
                output_path = out_dir / filename

                # Write to disk
                output_path.write_text(rendered, encoding="utf-8")
                stored_count += 1

            except Exception as e:
                console.print(
                    f"[red]Error rendering {product_id} × {template_basename}: {e}[/red]"
                )
                raise typer.Exit(1)

    console.print(f"[green]Stored {stored_count} prompts in {out_dir}[/green]")


if __name__ == "__main__":
    app()
