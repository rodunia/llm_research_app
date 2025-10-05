"""Smoke matrix generator for LLM experiments with prompt indexing."""

import csv
import hashlib
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.table import Table

from runner.render import load_product_yaml, create_jinja_env, render_prompt

app = typer.Typer(help="Generate smoke test matrix with indexed prompts")
console = Console()


@dataclass
class ExperimentRun:
    """Configuration for a single experimental run."""

    product_id: str
    template: str
    time_of_day: str
    temperature: float
    repetition: int
    engine: str
    trap_flag: bool

    def to_canonical_dict(self) -> dict:
        """Convert to canonical dictionary for hashing."""
        return {
            "product_id": self.product_id,
            "template": self.template,
            "time_of_day": self.time_of_day,
            "temperature": self.temperature,
            "repetition": self.repetition,
            "engine": self.engine,
            "trap_flag": self.trap_flag,
        }


def compute_run_id(run: ExperimentRun, rendered_prompt: str) -> str:
    """Compute stable run_id using SHA1 of canonical JSON + rendered prompt.

    Args:
        run: Experiment run configuration
        rendered_prompt: Rendered prompt text

    Returns:
        First 16 characters of SHA1 hash
    """
    canonical = run.to_canonical_dict()
    # Sort keys for deterministic JSON
    canonical_json = json.dumps(canonical, sort_keys=True)

    # Combine config + prompt
    combined = canonical_json + rendered_prompt

    # Compute SHA1 hash
    hash_obj = hashlib.sha1(combined.encode("utf-8"))
    return hash_obj.hexdigest()[:16]


def generate_smoke_matrix(trap_flag: bool = False) -> List[ExperimentRun]:
    """Generate smoke test matrix configuration.

    Smoke set: 3 products × 5 templates × 1 time × 1 temp × 1 rep × 1 engine = 15 items

    Args:
        trap_flag: Whether to enable people-pleasing trap

    Returns:
        List of ExperimentRun configurations
    """
    # Smoke test constants (single values for each dimension)
    products = ["supplement_melatonin", "smartphone_mid", "cryptocurrency_corecoin"]
    templates = [
        "digital_ad.j2",
        "organic_social_posts.j2",
        "faq.j2",
        "spec_document_facts_only.j2",
        "blog_post_promo.j2",
    ]
    time_of_day = "morning"
    temperature = 0.6
    repetition = 1
    engine = "anthropic"

    runs = []
    for product_id in products:
        for template in templates:
            run = ExperimentRun(
                product_id=product_id,
                template=template,
                time_of_day=time_of_day,
                temperature=temperature,
                repetition=repetition,
                engine=engine,
                trap_flag=trap_flag,
            )
            runs.append(run)

    return runs


def get_product_filename(product_id: str, products_dir: Path) -> Path:
    """Map product_id to actual YAML filename.

    Args:
        product_id: Product identifier from experiment config
        products_dir: Directory containing product YAML files

    Returns:
        Path to product YAML file

    Raises:
        FileNotFoundError: If no matching product file found
    """
    # Mapping of product_id to filename (without .yaml extension)
    filename_map = {
        "supplement_melatonin": "supplement_melatonin",
        "smartphone_mid": "smartphone",
        "cryptocurrency_corecoin": "cryptocurrency",
    }

    filename_base = filename_map.get(product_id, product_id)
    product_file = products_dir / f"{filename_base}.yaml"

    if not product_file.exists():
        raise FileNotFoundError(f"Product file not found: {product_file}")

    return product_file


def render_and_save_prompt(
    run: ExperimentRun,
    products_dir: Path,
    templates_dir: Path,
    output_dir: Path,
    jinja_env,
) -> tuple[str, str, int]:
    """Render a prompt and save to disk with deterministic filename.

    Args:
        run: Experiment run configuration
        products_dir: Directory containing product YAML files
        templates_dir: Directory containing Jinja2 templates
        output_dir: Output directory for prompt files
        jinja_env: Configured Jinja2 Environment

    Returns:
        Tuple of (run_id, filepath, prompt_length)
    """
    # Load product data using filename mapping
    product_file = get_product_filename(run.product_id, products_dir)
    product_data = load_product_yaml(product_file)

    # Render prompt
    rendered_prompt = render_prompt(
        product_data=product_data,
        template_name=run.template,
        jinja_env=jinja_env,
        trap_flag=run.trap_flag,
    )

    # Compute stable run_id
    run_id = compute_run_id(run, rendered_prompt)

    # Generate filename: {run_id}__{product_id}__{template_basename}.txt
    template_basename = Path(run.template).stem
    filename = f"{run_id}__{run.product_id}__{template_basename}.txt"
    filepath = output_dir / filename

    # Write prompt to disk
    filepath.write_text(rendered_prompt, encoding="utf-8")

    return run_id, str(filepath), len(rendered_prompt)


def write_index_csv(
    index_data: List[dict],
    csv_path: Path,
    append: bool = False,
) -> None:
    """Write or append to prompts index CSV.

    Args:
        index_data: List of index row dictionaries
        csv_path: Path to CSV file
        append: Whether to append (True) or overwrite (False)
    """
    fieldnames = [
        "run_id",
        "product_id",
        "template",
        "time_of_day",
        "temperature",
        "repetition",
        "engine",
        "trap_flag",
        "filepath",
        "prompt_len",
    ]

    mode = "a" if append else "w"
    write_header = not append or not csv_path.exists()

    csv_path.parent.mkdir(parents=True, exist_ok=True)

    with open(csv_path, mode=mode, newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerows(index_data)


@app.command()
def main(
    products_dir: Path = typer.Option(
        Path("products"), help="Directory containing product YAML files"
    ),
    templates_dir: Path = typer.Option(
        Path("prompts"), help="Directory containing Jinja2 templates"
    ),
    output_dir: Path = typer.Option(
        Path("outputs/prompts"), help="Output directory for prompt files"
    ),
    results_dir: Path = typer.Option(
        Path("results"), help="Directory for results/index CSV"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Print first 5 run IDs without creating files"
    ),
    trap: bool = typer.Option(
        False, "--trap", help="Generate only trap-enabled prompts"
    ),
    both: bool = typer.Option(
        False, "--both", help="Generate both normal and trap prompts"
    ),
) -> None:
    """Generate smoke test matrix with indexed prompts.

    Default: Generate 15 normal prompts (trap_flag=False)
    --trap: Generate 15 trap prompts (trap_flag=True)
    --both: Generate 30 prompts (15 normal + 15 trap)
    """
    # Validate input directories
    if not products_dir.exists():
        console.print(f"[red]Error: Products directory not found: {products_dir}[/red]")
        raise typer.Exit(1)

    if not templates_dir.exists():
        console.print(f"[red]Error: Templates directory not found: {templates_dir}[/red]")
        raise typer.Exit(1)

    # Determine which sets to generate
    if both:
        generate_sets = [False, True]  # Normal + Trap
    elif trap:
        generate_sets = [True]  # Trap only
    else:
        generate_sets = [False]  # Normal only (default)

    # Generate matrix configurations
    all_runs = []
    for trap_flag in generate_sets:
        runs = generate_smoke_matrix(trap_flag=trap_flag)
        all_runs.extend(runs)

    console.print(f"[cyan]Generated {len(all_runs)} experiment runs[/cyan]")

    # Dry run mode: print first 5 run_ids
    if dry_run:
        console.print("\n[yellow]DRY RUN MODE - First 5 run IDs:[/yellow]")
        jinja_env = create_jinja_env(templates_dir)

        for i, run in enumerate(all_runs[:5]):
            product_file = get_product_filename(run.product_id, products_dir)
            product_data = load_product_yaml(product_file)
            rendered = render_prompt(
                product_data=product_data,
                template_name=run.template,
                jinja_env=jinja_env,
                trap_flag=run.trap_flag,
            )
            run_id = compute_run_id(run, rendered)
            console.print(f"{i + 1}. {run_id} (trap={run.trap_flag})")

        return

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create Jinja environment
    jinja_env = create_jinja_env(templates_dir)

    # Generate and save prompts
    index_data = []
    for run in all_runs:
        try:
            run_id, filepath, prompt_len = render_and_save_prompt(
                run=run,
                products_dir=products_dir,
                templates_dir=templates_dir,
                output_dir=output_dir,
                jinja_env=jinja_env,
            )

            # Add to index
            index_row = {
                "run_id": run_id,
                "product_id": run.product_id,
                "template": run.template,
                "time_of_day": run.time_of_day,
                "temperature": run.temperature,
                "repetition": run.repetition,
                "engine": run.engine,
                "trap_flag": run.trap_flag,
                "filepath": filepath,
                "prompt_len": prompt_len,
            }
            index_data.append(index_row)

        except Exception as e:
            console.print(f"[red]Error processing {run.product_id} × {run.template}: {e}[/red]")
            raise typer.Exit(1)

    # Write index CSV
    csv_path = results_dir / "prompts_index.csv"
    write_index_csv(index_data, csv_path, append=False)

    # Summary
    console.print(f"\n[green]✓ Created {len(index_data)} prompt files[/green]")
    console.print(f"[green]✓ Wrote index to {csv_path}[/green]")

    # Show summary table
    table = Table(title="Generation Summary")
    table.add_column("Mode", style="cyan")
    table.add_column("Count", style="bold")

    normal_count = sum(1 for row in index_data if not row["trap_flag"])
    trap_count = sum(1 for row in index_data if row["trap_flag"])

    if normal_count:
        table.add_row("Normal (trap=False)", str(normal_count))
    if trap_count:
        table.add_row("Trap (trap=True)", str(trap_count))
    table.add_row("Total", str(len(index_data)))

    console.print(table)


if __name__ == "__main__":
    app()
