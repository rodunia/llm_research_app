"""Database storage for experiment results with proper data integrity."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone


class ExperimentDB:
    """SQLite database for storing experiment results with ACID guarantees."""

    def __init__(self, db_path: Path = Path("data/results.db")):
        """Initialize database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def get_connection(self):
        """Context manager for database connections with transaction support.

        Yields:
            sqlite3.Connection: Database connection with row factory enabled

        Example:
            with db.get_connection() as conn:
                conn.execute("INSERT INTO ...")
                # Automatic commit on success, rollback on error
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row  # Access columns by name
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_schema(self) -> None:
        """Create database tables if they don't exist."""
        with self.get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS experiment_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    account_id TEXT NOT NULL,
                    run_timestamp TEXT NOT NULL,
                    repetition_id INTEGER NOT NULL,
                    prompt_id TEXT NOT NULL,
                    prompt_text TEXT NOT NULL,
                    system_prompt TEXT,
                    conversation_id TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    model_version TEXT NOT NULL,
                    temperature REAL NOT NULL,
                    max_tokens INTEGER,
                    top_p REAL,
                    frequency_penalty REAL,
                    presence_penalty REAL,
                    seed INTEGER,
                    output_text TEXT,
                    finish_reason TEXT,
                    prompt_tokens INTEGER,
                    completion_tokens INTEGER,
                    total_tokens INTEGER,
                    tags TEXT,
                    researcher_notes TEXT,
                    success BOOLEAN NOT NULL DEFAULT 1,
                    error_type TEXT,
                    error_message TEXT,
                    product_id TEXT,
                    template TEXT,
                    trap_flag TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indexes separately
            conn.execute("CREATE INDEX IF NOT EXISTS idx_session ON experiment_results(session_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_model ON experiment_results(model_name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON experiment_results(run_timestamp)")

    def save_result(self, data: Dict[str, Any]) -> int:
        """Save experiment result to database.

        Args:
            data: Dictionary containing experiment result data

        Returns:
            int: Row ID of inserted record

        Raises:
            sqlite3.Error: If database operation fails
        """
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO experiment_results (
                    session_id, account_id, run_timestamp, repetition_id,
                    prompt_id, prompt_text, system_prompt, conversation_id,
                    model_name, model_version, temperature, max_tokens,
                    top_p, frequency_penalty, presence_penalty, seed,
                    output_text, finish_reason, prompt_tokens,
                    completion_tokens, total_tokens, tags, researcher_notes,
                    success, error_type, error_message,
                    product_id, template, trap_flag
                ) VALUES (
                    :session_id, :account_id, :run_timestamp, :repetition_id,
                    :prompt_id, :prompt_text, :system_prompt, :conversation_id,
                    :model_name, :model_version, :temperature, :max_tokens,
                    :top_p, :frequency_penalty, :presence_penalty, :seed,
                    :output_text, :finish_reason, :prompt_tokens,
                    :completion_tokens, :total_tokens, :tags, :researcher_notes,
                    :success, :error_type, :error_message,
                    :product_id, :template, :trap_flag
                )
            """, data)
            return cursor.lastrowid

    def get_session_results(self, session_id: str) -> List[Dict[str, Any]]:
        """Retrieve all results for a session.

        Args:
            session_id: Session identifier

        Returns:
            List of result dictionaries
        """
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM experiment_results WHERE session_id = ? ORDER BY run_timestamp",
                (session_id,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def export_to_csv(self, output_path: Path, session_id: Optional[str] = None) -> None:
        """Export results to CSV file.

        Args:
            output_path: Path to output CSV file
            session_id: Optional session ID to filter results
        """
        import csv

        with self.get_connection() as conn:
            if session_id:
                cursor = conn.execute(
                    "SELECT * FROM experiment_results WHERE session_id = ? ORDER BY run_timestamp",
                    (session_id,)
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM experiment_results ORDER BY run_timestamp"
                )

            rows = cursor.fetchall()
            if not rows:
                return

            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows([dict(row) for row in rows])


def save_results(session_id: str, account_id: str, results: List[Dict[str, Any]]) -> None:
    """Save experiment results to database (wrapper for backward compatibility).

    Args:
        session_id: Session identifier
        account_id: Account/researcher identifier
        results: List of result dictionaries from LLM calls

    Note:
        This is a convenience wrapper around ExperimentDB.save_result()
        for backward compatibility with test scripts.
    """
    db = ExperimentDB()

    for result in results:
        # Enrich result with session/account info if not present
        data = {
            "session_id": session_id,
            "account_id": account_id,
            "run_timestamp": datetime.now(timezone.utc).isoformat(),
            "repetition_id": 0,
            "prompt_id": "test",
            "prompt_text": result.get("prompt_text", ""),
            "system_prompt": result.get("system_prompt"),
            "conversation_id": f"{session_id}_0",
            "model_name": result.get("model_name", "unknown"),
            "model_version": result.get("model_version", "unknown"),
            "temperature": result.get("temperature", 0.7),
            "max_tokens": result.get("max_tokens"),
            "top_p": result.get("top_p"),
            "frequency_penalty": result.get("frequency_penalty"),
            "presence_penalty": result.get("presence_penalty"),
            "seed": result.get("seed"),
            "output_text": result.get("output_text", ""),
            "finish_reason": result.get("finish_reason", ""),
            "prompt_tokens": result.get("prompt_tokens", 0),
            "completion_tokens": result.get("completion_tokens", 0),
            "total_tokens": result.get("total_tokens", 0),
            "tags": result.get("tags"),
            "researcher_notes": result.get("researcher_notes"),
            "success": result.get("finish_reason") not in ["error", "failed"],
            "error_type": result.get("error_type"),
            "error_message": result.get("error_message"),
            "product_id": result.get("product_id"),
            "template": result.get("template"),
            "trap_flag": result.get("trap_flag"),
        }
        db.save_result(data)
