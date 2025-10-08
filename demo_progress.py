"""Demo script showing progress bar behavior.

This simulates what you'll see during actual execution,
but with faster timing for demonstration purposes.
"""

import time
from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn, TimeElapsedColumn

console = Console()

def demo_progress():
    """Simulate LLM execution progress."""

    console.print("\n[bold cyan]Demo: LLM Execution Progress Display[/bold cyan]\n")
    console.print("This shows what you'll see during 'python orchestrator.py run --time-of-day morning'\n")

    # Simulate 20 runs (much smaller than real 405)
    total_runs = 20
    engines = ["openai", "google", "mistral"]
    products = ["smartphone_mid", "cryptocurrency_corecoin", "supplement_melatonin"]

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("•"),
        TextColumn("{task.completed}/{task.total}"),
        TextColumn("•"),
        TimeElapsedColumn(),
        TextColumn("•"),
        TimeRemainingColumn(),
        console=console
    ) as progress:

        task = progress.add_task(
            "[cyan]Executing LLM runs...",
            total=total_runs
        )

        for i in range(total_runs):
            # Simulate varying run times (real runs take 1-5 seconds each)
            engine = engines[i % 3]
            product = products[i % 3]
            run_id = f"abc{i:03d}def{i:02d}ghi"

            # Update description with current job
            progress.update(
                task,
                description=f"[cyan]Run {i+1}/{total_runs} | {engine} | {product} | {run_id[:12]}"
            )

            # Simulate API call (much faster than real 1-5 seconds)
            time.sleep(0.5)

            # Simulate occasional error
            if i == 7:
                console.print(f"[red]✗ Failed {run_id[:12]}: Rate limit (will retry)[/red]")

            progress.advance(task)

    # Show final summary
    console.print("\n[bold]Execution Summary[/bold]")
    console.print(f"[green]✓ Completed: 19[/green]")
    console.print(f"[red]✗ Failed: 1[/red]")
    console.print(f"[cyan]⏱ Total time: 10.2s (0.5s per run)[/cyan]")
    console.print(f"[cyan]📊 Success rate: 95.0%[/cyan]")

    console.print("\n[dim]In real execution with 405 runs, expect ~30-60 minutes total.[/dim]\n")


if __name__ == "__main__":
    demo_progress()
