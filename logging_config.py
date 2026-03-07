"""Centralized logging configuration for LLM research experiments.

This module provides unified logging setup for:
- Session-level logs (orchestrator runs)
- Run-level logs (individual LLM executions)
- Module-level logs (engines, analysis, etc.)

All logs follow ISO 8601 timestamps for reproducibility.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional


# Log directories
LOG_DIR = Path("logs")
RUN_LOGS = LOG_DIR / "runs"
SESSION_LOGS = LOG_DIR / "sessions"
ERROR_LOGS = LOG_DIR / "errors"

# Create directories on import
for dir_path in [RUN_LOGS, SESSION_LOGS, ERROR_LOGS]:
    dir_path.mkdir(parents=True, exist_ok=True)


def setup_logging(
    name: str,
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    console: bool = True,
    format_string: Optional[str] = None
) -> logging.Logger:
    """Configure logger with file + console handlers.

    Args:
        name: Logger name (typically __name__)
        level: Logging level (e.g., logging.INFO, logging.DEBUG)
        log_file: Optional log file path (absolute or relative to project root)
        console: Enable console output (default: True)
        format_string: Custom format string (default: timestamp | level | module | message)

    Returns:
        Configured logger

    Example:
        >>> logger = setup_logging(__name__, log_file="logs/sessions/pilot.log")
        >>> logger.info("Starting experiment")
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.handlers = []  # Clear existing handlers to avoid duplicates

    # Default format: ISO 8601 timestamp | level | module | message
    if format_string is None:
        format_string = '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'

    formatter = logging.Formatter(
        format_string,
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # File handler (if specified)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        fh = logging.FileHandler(log_path, encoding='utf-8')
        fh.setLevel(level)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    # Console handler (stderr for logs, stdout for user-facing output)
    if console:
        ch = logging.StreamHandler(sys.stderr)
        ch.setLevel(level)
        ch.setFormatter(formatter)
        logger.addHandler(ch)

    return logger


def get_session_log_path(session_name: str) -> Path:
    """Generate log path for experimental session.

    Args:
        session_name: Session identifier (e.g., "pilot_morning", "full_experiment")

    Returns:
        Path to session log file: logs/sessions/{session_name}_{timestamp}.log

    Example:
        >>> path = get_session_log_path("pilot_morning")
        >>> # Returns: logs/sessions/pilot_morning_20260307_140532.log
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return SESSION_LOGS / f"{session_name}_{timestamp}.log"


def get_run_log_path(run_id: str) -> Path:
    """Generate log path for individual run.

    Args:
        run_id: Run identifier (deterministic hash from knobs + prompt)

    Returns:
        Path to run log file: logs/runs/{run_id}.log

    Example:
        >>> path = get_run_log_path("abc123def456")
        >>> # Returns: logs/runs/abc123def456.log
    """
    return RUN_LOGS / f"{run_id}.log"


def get_error_log_path(component: str) -> Path:
    """Generate log path for error tracking.

    Args:
        component: Component identifier (e.g., "glass_box_audit", "openai_client")

    Returns:
        Path to error log file: logs/errors/{component}_{timestamp}.log

    Example:
        >>> path = get_error_log_path("glass_box_audit")
        >>> # Returns: logs/errors/glass_box_audit_20260307_140532.log
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return ERROR_LOGS / f"{component}_{timestamp}.log"


def log_environment_info(logger: logging.Logger) -> None:
    """Log system environment for reproducibility.

    Captures:
    - Python version
    - Platform
    - Git commit (if available)
    - Key package versions

    Args:
        logger: Logger instance to write to

    Example:
        >>> logger = setup_logging(__name__)
        >>> log_environment_info(logger)
    """
    import subprocess
    import platform

    logger.info("="*60)
    logger.info("ENVIRONMENT INFORMATION")
    logger.info("="*60)

    # Python version
    logger.info(f"Python: {sys.version.split()[0]} ({platform.python_implementation()})")
    logger.info(f"Platform: {platform.platform()}")
    logger.info(f"Architecture: {platform.machine()}")

    # Git commit
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True
        ).strip()
        logger.info(f"Git commit: {commit[:12]}")
    except:
        logger.warning("Git commit unknown (not in repository or git not available)")

    # Key dependencies
    logger.info("Key dependencies:")
    try:
        import pkg_resources
        for pkg in ["openai", "transformers", "torch", "pandas", "rich", "typer"]:
            try:
                version = pkg_resources.get_distribution(pkg).version
                logger.info(f"  {pkg}: {version}")
            except:
                logger.warning(f"  {pkg}: not installed")
    except ImportError:
        logger.warning("pkg_resources not available, skipping dependency versions")

    logger.info("="*60)


# Default logger for this module
logger = setup_logging(__name__)
