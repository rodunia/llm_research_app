# Archived Files

This directory contains deprecated code that is no longer part of the active codebase.

## Files

### `main.py` (Archived: 2025-10-06)
**Reason**: Interactive CLI workflow deprecated in favor of batch-only workflow.

The interactive CLI (`main.py`) was the original interface for manually running single LLM queries with CSV logging. It has been deprecated because:
- Conflicted with batch processing system (`orchestrator.py` + `runner/`)
- Used separate CSV storage (`results.csv`) incompatible with experimental matrix
- Not needed for systematic research experiments

**If you need manual testing**: Use `test_run.py` or `test_comprehensive.py` instead.

### `storage.py` (Archived: 2025-10-06)
**Reason**: SQLite storage abandoned in favor of CSV-first approach.

`core/storage.py` implemented SQLite database storage but was never integrated into the actual workflow. Removed because:
- CSV is easier for non-programmers to work with (Excel/Google Sheets)
- SQLite adds unnecessary complexity
- Current system works well with CSV + flat files

**Current storage**: All data tracked in `results/experiments.csv` with outputs in `outputs/*.txt`.

---

## Restoration

If you need to restore these files:

```bash
# Restore main.py
cp archive/main.py main.py

# Restore storage.py
cp archive/storage.py core/storage.py
```

**Note**: Restored files may not work without modifications due to architectural changes (experiments.csv, ENGINE_MODELS config, etc.).
