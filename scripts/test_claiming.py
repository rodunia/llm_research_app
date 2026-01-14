"""Concurrency test for multi-user atomic job claiming.

Tests that multiple users can claim jobs concurrently without duplicate work.

Usage:
    python scripts/test_claiming.py
"""

import csv
import hashlib
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Tuple

from rich.console import Console
from rich.table import Table

console = Console()


def create_test_dataset(n_jobs: int = 30) -> str:
    """Create a small test dataset for concurrency testing.

    Args:
        n_jobs: Number of test jobs to create

    Returns:
        Path to test CSV file
    """
    test_csv = Path("results/test_experiments.csv")
    test_db = Path("results/test_experiments.db")

    # Clean up previous test artifacts
    if test_csv.exists():
        test_csv.unlink()
    if test_db.exists():
        test_db.unlink()

    # Create test CSV with minimal fields
    fieldnames = [
        "run_id",
        "status",
        "engine",
        "product_id",
        "material_type",
        "time_of_day_label",
        "temperature_label",
        "repetition_id",
        "trap_flag",
        "output_path",
        "started_at",
        "completed_at",
        "model",
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "finish_reason"
    ]

    rows = []
    for i in range(n_jobs):
        run_id = hashlib.md5(f"test_job_{i}".encode()).hexdigest()
        rows.append({
            "run_id": run_id,
            "status": "pending",
            "engine": ["openai", "google", "mistral"][i % 3],
            "product_id": "smartphone_mid",
            "material_type": "digital_ad.j2",
            "time_of_day_label": "morning",
            "temperature_label": "0.6",
            "repetition_id": "1",
            "trap_flag": "False",
            "output_path": "",
            "started_at": "",
            "completed_at": "",
            "model": "",
            "prompt_tokens": "0",
            "completion_tokens": "0",
            "total_tokens": "0",
            "finish_reason": ""
        })

    with open(test_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    console.print(f"[green]✓ Created test dataset: {n_jobs} jobs in {test_csv}[/green]")
    return str(test_csv)


def claim_jobs_for_user(
    user: str,
    csv_path: str,
    db_path: str,
    max_jobs: int,
    delay: float = 0
) -> Tuple[str, List[str], float]:
    """Claim jobs for a simulated user.

    Args:
        user: User identifier
        csv_path: Path to experiments CSV
        db_path: Path to SQLite database
        max_jobs: Maximum jobs to claim
        delay: Artificial delay before claiming (for timing variation)

    Returns:
        Tuple of (user, claimed_run_ids, elapsed_time)
    """
    if delay > 0:
        time.sleep(delay)

    cmd = [
        sys.executable,
        "-m",
        "runner.run_job",
        "batch",
        "--from-index", csv_path,
        "--db-path", db_path,
        "--user", user,
        "--max-jobs", str(max_jobs),
        "--claim-only"  # Don't execute, just claim
    ]

    start = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.time() - start

    # Parse claimed run_ids from output
    claimed_run_ids = []
    if result.returncode == 0:
        # Look for "Claimed N jobs" in output
        for line in result.stdout.split("\n"):
            if "Claimed" in line and "jobs" in line:
                # Extract count from line like "✓ Claimed 10 jobs"
                try:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == "Claimed" and i + 1 < len(parts):
                            claimed_count = int(parts[i + 1])
                            # Store count (we don't have individual IDs from claim-only output)
                            claimed_run_ids = [f"job_{j}" for j in range(claimed_count)]
                            break
                except (ValueError, IndexError):
                    pass

    return user, claimed_run_ids, elapsed


def verify_no_duplicates(db_path: str) -> Tuple[bool, dict]:
    """Verify that no jobs were claimed by multiple users.

    Args:
        db_path: Path to SQLite database

    Returns:
        Tuple of (is_valid, stats_dict)
    """
    from runner.job_store import get_db_connection

    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()

        # Get all claimed jobs grouped by run_id
        cursor.execute("""
            SELECT run_id, claimed_by, status
            FROM jobs
            WHERE status IN ('claimed', 'running', 'completed')
        """)

        claimed_jobs = {}
        for row in cursor.fetchall():
            run_id = row["run_id"]
            claimed_by = row["claimed_by"]
            status = row["status"]

            if run_id not in claimed_jobs:
                claimed_jobs[run_id] = []
            claimed_jobs[run_id].append((claimed_by, status))

        # Check for duplicates
        duplicates = {}
        for run_id, claimants in claimed_jobs.items():
            if len(claimants) > 1:
                duplicates[run_id] = claimants

        # Get status counts by user
        cursor.execute("""
            SELECT claimed_by, COUNT(*) as count
            FROM jobs
            WHERE status = 'claimed'
            GROUP BY claimed_by
        """)

        user_counts = {row["claimed_by"]: row["count"] for row in cursor.fetchall()}

        # Get overall status counts
        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM jobs
            GROUP BY status
        """)

        status_counts = {row["status"]: row["count"] for row in cursor.fetchall()}

        stats = {
            "duplicates": duplicates,
            "user_counts": user_counts,
            "status_counts": status_counts,
            "total_jobs": sum(status_counts.values())
        }

        return len(duplicates) == 0, stats


def run_concurrency_test(n_jobs: int = 30, n_users: int = 3, jobs_per_user: int = 10):
    """Run full concurrency test.

    Args:
        n_jobs: Total number of test jobs
        n_users: Number of simulated users
        jobs_per_user: Max jobs each user can claim
    """
    console.print("\n[bold]Multi-User Claiming Concurrency Test[/bold]\n")

    # Step 1: Create test dataset
    csv_path = create_test_dataset(n_jobs)
    db_path = "results/test_experiments.db"

    # Step 2: Initialize DB from CSV
    from runner.job_store import initialize_db
    initialize_db(csv_path=csv_path, db_path=db_path)
    console.print(f"[green]✓ Initialized DB from CSV[/green]\n")

    # Step 3: Simulate concurrent claiming
    console.print(f"[cyan]Simulating {n_users} users claiming jobs concurrently...[/cyan]")

    users = [f"user_{i+1}" for i in range(n_users)]
    delays = [i * 0.01 for i in range(n_users)]  # Stagger start by 10ms

    results = []
    with ThreadPoolExecutor(max_workers=n_users) as executor:
        futures = {
            executor.submit(
                claim_jobs_for_user,
                user=user,
                csv_path=csv_path,
                db_path=db_path,
                max_jobs=jobs_per_user,
                delay=delay
            ): user
            for user, delay in zip(users, delays)
        }

        for future in as_completed(futures):
            user = futures[future]
            try:
                result_user, claimed_ids, elapsed = future.result()
                results.append((result_user, len(claimed_ids), elapsed))
                console.print(f"[green]✓ {result_user}: Claimed {len(claimed_ids)} jobs in {elapsed:.2f}s[/green]")
            except Exception as e:
                console.print(f"[red]✗ {user} failed: {e}[/red]")

    # Step 4: Verify no duplicates
    console.print("\n[cyan]Verifying claim integrity...[/cyan]")
    is_valid, stats = verify_no_duplicates(db_path)

    # Step 5: Display results
    console.print("\n[bold]Test Results[/bold]\n")

    # Create summary table
    table = Table(title="Claim Summary by User")
    table.add_column("User", style="cyan")
    table.add_column("Jobs Claimed", justify="right", style="green")

    total_claimed = 0
    for user, count, elapsed in sorted(results):
        table.add_row(user, str(count))
        total_claimed += count

    console.print(table)

    # Status counts
    console.print(f"\n[bold]Overall Status:[/bold]")
    console.print(f"  Total jobs: {stats['total_jobs']}")
    console.print(f"  Pending: {stats['status_counts'].get('pending', 0)}")
    console.print(f"  Claimed: {stats['status_counts'].get('claimed', 0)}")
    console.print(f"  Total claimed: {total_claimed}")

    # Duplicate check
    if is_valid:
        console.print(f"\n[bold green]✓ PASS: No duplicate claims detected[/bold green]")
    else:
        console.print(f"\n[bold red]✗ FAIL: {len(stats['duplicates'])} duplicate claims detected[/bold red]")
        for run_id, claimants in stats['duplicates'].items():
            console.print(f"  {run_id[:12]}: {claimants}")

    # Verify math
    expected_claimed = min(n_jobs, n_users * jobs_per_user)
    if total_claimed == stats['status_counts'].get('claimed', 0):
        console.print(f"[green]✓ Claim counts consistent: {total_claimed} total[/green]")
    else:
        console.print(f"[red]✗ Claim count mismatch: {total_claimed} reported vs {stats['status_counts'].get('claimed', 0)} in DB[/red]")

    # Final verdict
    all_checks_passed = (
        is_valid and
        total_claimed == stats['status_counts'].get('claimed', 0) and
        total_claimed <= expected_claimed
    )

    if all_checks_passed:
        console.print("\n[bold green]✅ All concurrency tests PASSED[/bold green]\n")
        return 0
    else:
        console.print("\n[bold red]❌ Some concurrency tests FAILED[/bold red]\n")
        return 1


if __name__ == "__main__":
    exit_code = run_concurrency_test(
        n_jobs=30,      # Create 30 test jobs
        n_users=3,      # Simulate 3 concurrent users
        jobs_per_user=10  # Each user tries to claim 10 jobs
    )
    sys.exit(exit_code)
