"""Test script to verify all LLM engine clients are working correctly.

This script tests:
1. API key configuration
2. Basic connectivity to each provider
3. Response format validation

Run before executing the full experimental pipeline.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

# Load environment variables
load_dotenv()

console = Console()

# Simple test prompt
TEST_PROMPT = "Say 'Hello, I am working correctly!' in exactly those words."


def test_openai():
    """Test OpenAI API connectivity."""
    from runner.engines.openai_client import call_openai

    console.print("\n[cyan]Testing OpenAI...[/cyan]")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        console.print("[red]✗ OPENAI_API_KEY not found in .env[/red]")
        return False

    try:
        response = call_openai(
            prompt=TEST_PROMPT,
            temperature=0.7,
            model="gpt-4o-mini",  # Use cheaper model for testing
            max_tokens=50
        )

        # Validate response structure
        assert "output_text" in response, "Missing output_text"
        assert "model" in response, "Missing model"
        assert "prompt_tokens" in response, "Missing prompt_tokens"
        assert "completion_tokens" in response, "Missing completion_tokens"
        assert "total_tokens" in response, "Missing total_tokens"
        assert "finish_reason" in response, "Missing finish_reason"

        console.print(f"[green]✓ OpenAI working[/green]")
        console.print(f"  Model: {response['model']}")
        console.print(f"  Tokens: {response['total_tokens']} (prompt: {response['prompt_tokens']}, completion: {response['completion_tokens']})")
        console.print(f"  Output: {response['output_text'][:100]}...")

        return True

    except Exception as e:
        console.print(f"[red]✗ OpenAI failed: {e}[/red]")
        return False


def test_google():
    """Test Google Gemini API connectivity."""
    from runner.engines.google_client import call_google

    console.print("\n[cyan]Testing Google Gemini...[/cyan]")

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        console.print("[red]✗ GOOGLE_API_KEY not found in .env[/red]")
        return False

    try:
        response = call_google(
            prompt=TEST_PROMPT,
            temperature=0.7,
            model="gemini-2.5-flash",  # Use available model
            max_tokens=50
        )

        # Validate response structure
        assert "output_text" in response, "Missing output_text"
        assert "model" in response, "Missing model"
        assert "prompt_tokens" in response, "Missing prompt_tokens"
        assert "completion_tokens" in response, "Missing completion_tokens"
        assert "total_tokens" in response, "Missing total_tokens"
        assert "finish_reason" in response, "Missing finish_reason"

        console.print(f"[green]✓ Google Gemini working[/green]")
        console.print(f"  Model: {response['model']}")
        console.print(f"  Tokens: {response['total_tokens']} (prompt: {response['prompt_tokens']}, completion: {response['completion_tokens']})")
        console.print(f"  Output: {response['output_text'][:100]}...")

        return True

    except Exception as e:
        console.print(f"[red]✗ Google Gemini failed: {e}[/red]")
        return False


def test_mistral():
    """Test Mistral API connectivity."""
    from runner.engines.mistral_client import call_mistral

    console.print("\n[cyan]Testing Mistral...[/cyan]")

    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        console.print("[red]✗ MISTRAL_API_KEY not found in .env[/red]")
        return False

    try:
        response = call_mistral(
            prompt=TEST_PROMPT,
            temperature=0.7,
            model="mistral-small-latest",
            max_tokens=50
        )

        # Validate response structure
        assert "output_text" in response, "Missing output_text"
        assert "model" in response, "Missing model"
        assert "prompt_tokens" in response, "Missing prompt_tokens"
        assert "completion_tokens" in response, "Missing completion_tokens"
        assert "total_tokens" in response, "Missing total_tokens"
        assert "finish_reason" in response, "Missing finish_reason"

        console.print(f"[green]✓ Mistral working[/green]")
        console.print(f"  Model: {response['model']}")
        console.print(f"  Tokens: {response['total_tokens']} (prompt: {response['prompt_tokens']}, completion: {response['completion_tokens']})")
        console.print(f"  Output: {response['output_text'][:100]}...")

        return True

    except Exception as e:
        console.print(f"[red]✗ Mistral failed: {e}[/red]")
        return False


def main():
    """Run all engine tests."""
    console.print(Panel.fit(
        "[bold]LLM Engine Connectivity Test[/bold]\n"
        "Testing OpenAI, Google Gemini, and Mistral API connections",
        border_style="cyan"
    ))

    results = {}

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:

        # Test OpenAI
        task = progress.add_task("Testing OpenAI...", total=None)
        results["openai"] = test_openai()
        progress.remove_task(task)

        # Test Google
        task = progress.add_task("Testing Google Gemini...", total=None)
        results["google"] = test_google()
        progress.remove_task(task)

        # Test Mistral
        task = progress.add_task("Testing Mistral...", total=None)
        results["mistral"] = test_mistral()
        progress.remove_task(task)

    # Summary table
    console.print("\n")
    table = Table(title="Engine Test Results", show_header=True, header_style="bold cyan")
    table.add_column("Engine", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Ready for Production", justify="center")

    for engine, status in results.items():
        status_icon = "[green]✓ PASS[/green]" if status else "[red]✗ FAIL[/red]"
        ready_icon = "[green]✓[/green]" if status else "[red]✗[/red]"
        table.add_row(engine.capitalize(), status_icon, ready_icon)

    console.print(table)

    # Final verdict
    all_pass = all(results.values())

    if all_pass:
        console.print("\n[bold green]✓ All engines working correctly![/bold green]")
        console.print("[green]You can proceed with the experimental pipeline.[/green]\n")
        return 0
    else:
        failed = [engine for engine, status in results.items() if not status]
        console.print(f"\n[bold red]✗ Some engines failed: {', '.join(failed)}[/bold red]")
        console.print("[yellow]Please check API keys in .env and try again.[/yellow]\n")
        return 1


if __name__ == "__main__":
    exit(main())
