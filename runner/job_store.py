"""SQLite-based job state store for atomic claiming and execution tracking.

Provides concurrent-safe job claiming for multi-user research execution.
experiments.csv remains the design matrix; experiments.db is authoritative for runtime state.
"""

import csv
import sqlite3
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional
from contextlib import contextmanager


def get_csv_hash(csv_path: Path) -> str:
    """Calculate MD5 hash of CSV content for sync detection.

    Args:
        csv_path: Path to CSV file

    Returns:
        MD5 hexdigest of CSV content
    """
    if not csv_path.exists():
        return "no_csv"

    with open(csv_path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


@contextmanager
def get_db_connection(db_path: str):
    """Context manager for database connections.

    Args:
        db_path: Path to SQLite database file

    Yields:
        sqlite3.Connection with row_factory set to Row
    """
    conn = sqlite3.connect(db_path, timeout=30.0)  # 30s timeout for lock contention
    conn.row_factory = sqlite3.Row  # Return rows as dict-like objects
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def ensure_schema(db_path: str) -> None:
    """Create jobs table and indices if they don't exist.

    Args:
        db_path: Path to SQLite database file
    """
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()

        # Create jobs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                run_id TEXT PRIMARY KEY,
                status TEXT NOT NULL DEFAULT 'pending',
                assigned_user TEXT,
                claimed_by TEXT,
                claimed_at TEXT,
                started_at TEXT,
                completed_at TEXT,
                session_id TEXT,
                engine TEXT NOT NULL,
                product_id TEXT NOT NULL,
                material_type TEXT NOT NULL,
                time_of_day_label TEXT,
                temperature_label TEXT,
                repetition_id INTEGER,
                trap_flag INTEGER DEFAULT 0,
                output_path TEXT,
                model TEXT,
                prompt_tokens INTEGER DEFAULT 0,
                completion_tokens INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0,
                finish_reason TEXT,
                error TEXT
            )
        """)

        # Create metadata table (for sync tracking)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        # Create indices for efficient queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_engine ON jobs(engine)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_time_of_day ON jobs(time_of_day_label)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_assigned_user ON jobs(assigned_user)")

        conn.commit()


def initialize_db(
    csv_path: str = "results/experiments.csv",
    db_path: str = "results/experiments.db",
    force_sync: bool = False
) -> None:
    """Initialize database from CSV if needed.

    Args:
        csv_path: Path to experiments CSV (design matrix)
        db_path: Path to SQLite database
        force_sync: If True, re-sync even if CSV hash matches
    """
    csv_file = Path(csv_path)
    db_file = Path(db_path)

    if not csv_file.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    # Ensure schema exists
    ensure_schema(db_path)

    # Check if we need to sync
    current_hash = get_csv_hash(csv_file)

    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()

        # Check stored hash
        cursor.execute("SELECT value FROM metadata WHERE key = 'csv_hash'")
        row = cursor.fetchone()
        stored_hash = row["value"] if row else None

        if stored_hash == current_hash and not force_sync:
            # Already synced
            return

        if stored_hash and stored_hash != current_hash and not force_sync:
            # CSV changed - warn but allow (could add --force-sync flag)
            print(f"Warning: CSV changed since last sync (hash mismatch)")
            print(f"  Stored: {stored_hash}")
            print(f"  Current: {current_hash}")
            print(f"  Use force_sync=True to re-initialize DB")
            return

        # Sync from CSV
        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        # Insert/update jobs
        for row in rows:
            # Prepare job record
            trap_flag = 1 if row.get("trap_flag", "False") == "True" else 0

            cursor.execute("""
                INSERT OR IGNORE INTO jobs (
                    run_id, status, engine, product_id, material_type,
                    time_of_day_label, temperature_label, repetition_id,
                    trap_flag, output_path, started_at, completed_at,
                    model, prompt_tokens, completion_tokens, total_tokens, finish_reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row.get("run_id"),
                row.get("status", "pending"),
                row.get("engine"),
                row.get("product_id"),
                row.get("material_type"),
                row.get("time_of_day_label"),
                row.get("temperature_label"),
                int(row.get("repetition_id", 0)),
                trap_flag,
                row.get("output_path", ""),
                row.get("started_at", ""),
                row.get("completed_at", ""),
                row.get("model", ""),
                int(row.get("prompt_tokens", 0)),
                int(row.get("completion_tokens", 0)),
                int(row.get("total_tokens", 0)),
                row.get("finish_reason", "")
            ))

        # Update hash
        cursor.execute("""
            INSERT OR REPLACE INTO metadata (key, value) VALUES ('csv_hash', ?)
        """, (current_hash,))

        conn.commit()


def claim_jobs(
    user: str,
    db_path: str = "results/experiments.db",
    filters: Optional[Dict[str, Any]] = None,
    limit: int = 10
) -> List[str]:
    """Atomically claim pending jobs for a user.

    Args:
        user: User identifier (e.g., "account_1")
        db_path: Path to SQLite database
        filters: Optional filters (engine, time_of_day, product_id, material_type, repetition_id)
        limit: Maximum number of jobs to claim

    Returns:
        List of claimed run_ids
    """
    if filters is None:
        filters = {}

    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()

        # Build WHERE clause from filters
        where_clauses = ["status = 'pending'"]
        params = []

        # Check assigned_user: if specified, only claim jobs assigned to this user OR null
        # This supports both assigned and shared pools
        if "assigned_user" in filters and filters["assigned_user"]:
            where_clauses.append("(assigned_user IS NULL OR assigned_user = ?)")
            params.append(filters["assigned_user"])

        if "engine" in filters and filters["engine"]:
            where_clauses.append("engine = ?")
            params.append(filters["engine"])

        if "time_of_day" in filters and filters["time_of_day"]:
            where_clauses.append("time_of_day_label = ?")
            params.append(filters["time_of_day"])

        if "product_id" in filters and filters["product_id"]:
            where_clauses.append("product_id = ?")
            params.append(filters["product_id"])

        if "material_type" in filters and filters["material_type"]:
            where_clauses.append("material_type = ?")
            params.append(filters["material_type"])

        if "repetition_id" in filters and filters["repetition_id"] is not None:
            where_clauses.append("repetition_id = ?")
            params.append(int(filters["repetition_id"]))

        where_clause = " AND ".join(where_clauses)

        # Atomic claim using UPDATE ... RETURNING (SQLite 3.35.0+)
        # If RETURNING not supported, fall back to SELECT + UPDATE
        try:
            # Try modern approach first
            from runner.utils import now_iso
            claimed_at = now_iso()

            cursor.execute(f"""
                UPDATE jobs
                SET status = 'claimed',
                    claimed_by = ?,
                    claimed_at = ?
                WHERE run_id IN (
                    SELECT run_id FROM jobs
                    WHERE {where_clause}
                    LIMIT ?
                )
                RETURNING run_id
            """, [user, claimed_at] + params + [limit])

            claimed_run_ids = [row["run_id"] for row in cursor.fetchall()]

        except sqlite3.OperationalError:
            # Fallback for older SQLite: SELECT then UPDATE
            cursor.execute(f"""
                SELECT run_id FROM jobs
                WHERE {where_clause}
                LIMIT ?
            """, params + [limit])

            run_ids_to_claim = [row["run_id"] for row in cursor.fetchall()]

            if run_ids_to_claim:
                from runner.utils import now_iso
                claimed_at = now_iso()

                placeholders = ",".join("?" * len(run_ids_to_claim))
                cursor.execute(f"""
                    UPDATE jobs
                    SET status = 'claimed',
                        claimed_by = ?,
                        claimed_at = ?
                    WHERE run_id IN ({placeholders})
                """, [user, claimed_at] + run_ids_to_claim)

            claimed_run_ids = run_ids_to_claim

        conn.commit()
        return claimed_run_ids


def mark_running(
    run_id: str,
    started_at: str,
    session_id: Optional[str] = None,
    db_path: str = "results/experiments.db"
) -> None:
    """Mark job as running.

    Args:
        run_id: Run identifier
        started_at: ISO timestamp when execution started
        session_id: Optional session identifier
        db_path: Path to SQLite database
    """
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE jobs
            SET status = 'running',
                started_at = ?,
                session_id = ?
            WHERE run_id = ?
        """, (started_at, session_id, run_id))
        conn.commit()


def mark_completed(
    run_id: str,
    completed_at: str,
    result: Dict[str, Any],
    db_path: str = "results/experiments.db"
) -> None:
    """Mark job as completed with results.

    Args:
        run_id: Run identifier
        completed_at: ISO timestamp when execution completed
        result: Result dict with model, tokens, finish_reason
        db_path: Path to SQLite database
    """
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE jobs
            SET status = 'completed',
                completed_at = ?,
                model = ?,
                prompt_tokens = ?,
                completion_tokens = ?,
                total_tokens = ?,
                finish_reason = ?
            WHERE run_id = ?
        """, (
            completed_at,
            result.get("model", ""),
            result.get("prompt_tokens", 0),
            result.get("completion_tokens", 0),
            result.get("total_tokens", 0),
            result.get("finish_reason", ""),
            run_id
        ))
        conn.commit()


def mark_failed(
    run_id: str,
    error: str,
    completed_at: str,
    db_path: str = "results/experiments.db"
) -> None:
    """Mark job as failed with error message.

    Args:
        run_id: Run identifier
        error: Error message
        completed_at: ISO timestamp when failure occurred
        db_path: Path to SQLite database
    """
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE jobs
            SET status = 'failed',
                completed_at = ?,
                error = ?
            WHERE run_id = ?
        """, (completed_at, error, run_id))
        conn.commit()


def get_job(run_id: str, db_path: str = "results/experiments.db") -> Optional[Dict[str, Any]]:
    """Get job details by run_id.

    Args:
        run_id: Run identifier
        db_path: Path to SQLite database

    Returns:
        Job dict or None if not found
    """
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM jobs WHERE run_id = ?", (run_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_status_counts(
    db_path: str = "results/experiments.db",
    filters: Optional[Dict[str, Any]] = None
) -> Dict[str, int]:
    """Get counts of jobs by status.

    Args:
        db_path: Path to SQLite database
        filters: Optional filters (engine, time_of_day, etc.)

    Returns:
        Dict with counts: {pending, claimed, running, completed, failed, total}
    """
    if filters is None:
        filters = {}

    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()

        # Build WHERE clause
        where_clauses = []
        params = []

        if "engine" in filters and filters["engine"]:
            where_clauses.append("engine = ?")
            params.append(filters["engine"])

        if "time_of_day" in filters and filters["time_of_day"]:
            where_clauses.append("time_of_day_label = ?")
            params.append(filters["time_of_day"])

        if "product_id" in filters and filters["product_id"]:
            where_clauses.append("product_id = ?")
            params.append(filters["product_id"])

        where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        # Get counts by status
        cursor.execute(f"""
            SELECT status, COUNT(*) as count
            FROM jobs
            {where_clause}
            GROUP BY status
        """, params)

        counts = {
            "pending": 0,
            "claimed": 0,
            "running": 0,
            "completed": 0,
            "failed": 0
        }

        for row in cursor.fetchall():
            counts[row["status"]] = row["count"]

        counts["total"] = sum(counts.values())
        return counts


def export_status_to_csv(
    csv_path: str = "results/experiments.csv",
    db_path: str = "results/experiments.db"
) -> None:
    """Export job statuses from DB back to CSV (for compatibility).

    Args:
        csv_path: Path to experiments CSV
        db_path: Path to SQLite database
    """
    csv_file = Path(csv_path)
    if not csv_file.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    # Read CSV
    with open(csv_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        if not rows:
            return
        fieldnames = list(rows[0].keys())

    # Get job statuses from DB
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT run_id, status, started_at, completed_at, model,
                   prompt_tokens, completion_tokens, total_tokens, finish_reason
            FROM jobs
        """)

        job_status = {}
        for row in cursor.fetchall():
            job_status[row["run_id"]] = dict(row)

    # Update rows with DB status
    for row in rows:
        run_id = row.get("run_id")
        if run_id in job_status:
            job = job_status[run_id]
            row["status"] = job["status"]
            row["started_at"] = job["started_at"] or ""
            row["completed_at"] = job["completed_at"] or ""
            row["model"] = job["model"] or ""
            row["prompt_tokens"] = job["prompt_tokens"] or 0
            row["completion_tokens"] = job["completion_tokens"] or 0
            row["total_tokens"] = job["total_tokens"] or 0
            row["finish_reason"] = job["finish_reason"] or ""

    # Write back to CSV
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
