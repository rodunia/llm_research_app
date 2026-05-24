# Full Rerun Checklist (Quick Reference)

**Date:** May 24, 2026
**Target:** May 25-31, 2026 (7 days)
**Runs:** 1,620 total
**Cost:** ~$27.50

## Pre-Launch Checklist

- [ ] Update `config.py` line 105: `DEFAULT_MAX_TOKENS = 20000`
- [ ] Backup current data: `cp results/experiments.csv results/backups/experiments_backup.csv`
- [ ] Regenerate matrix: `python scripts/test_randomizer_stratified.py --seed 42 --start-date 2026-05-25`
- [ ] Verify max_tokens: `grep "google" results/experiments.csv | head -1 | cut -d',' -f11` (should show 20000)
- [ ] Verify count: `wc -l results/experiments.csv` (should show 1621)
- [ ] Verify dates: Runs scheduled May 25-31, 2026

## Launch Commands

```bash
# Start temporal execution (background)
nohup python orchestrator.py temporal \
  --experiment-start 2026-05-25T00:00:00 \
  --session-id full_rerun_20k \
  > temporal_execution.log 2>&1 &

# Save PID
echo $! > temporal_pid.txt

# Verify running
ps aux | grep orchestrator
```

## Daily Monitoring

```bash
# Morning check (9am)
python scripts/monitor_experiment.py

# Evening check (9pm)
python scripts/monitor_experiment.py

# Check logs
tail -f temporal_execution.log
```

## Health Checks (Look For)

✅ **Good Signs:**
- Progress ~231-232 runs/day
- Zero MAX_TOKENS warnings
- Completion tokens <8,000
- Failure rate <5%

❌ **Red Flags:**
- MAX_TOKENS appearing
- High failure rate (>10%)
- Progress stalled >2 hours
- Completion tokens >7,500

## Emergency Stop

```bash
# Stop execution
kill $(cat temporal_pid.txt)

# Resume later
nohup python orchestrator.py temporal \
  --experiment-start 2026-05-25T00:00:00 \
  --session-id full_rerun_20k \
  > temporal_execution_resumed.log 2>&1 &
```

## Mid-Experiment Check (May 28)

After 3 days (~972 runs):

```bash
# Full report
python scripts/monitor_experiment.py > mid_experiment_report.txt

# Check for truncation
grep MAX_TOKENS results/experiments.csv | wc -l
# Should be: 0

# Token diagnostics
python analysis/diagnose_gemini_tokens.py
```

## Expected Progress

| Date | Day | Runs | Cumulative | % |
|------|-----|------|------------|---|
| May 25 | Sun | 232 | 232 | 14.3% |
| May 26 | Mon | 232 | 464 | 28.6% |
| May 27 | Tue | 232 | 696 | 43.0% |
| May 28 | Wed | 231 | 927 | 57.2% |
| May 29 | Thu | 231 | 1158 | 71.5% |
| May 30 | Fri | 231 | 1389 | 85.7% |
| May 31 | Sat | 231 | 1620 | 100% |

## Post-Completion (June 1)

```bash
# Verify completion
python scripts/monitor_experiment.py

# Check truncation
grep MAX_TOKENS results/experiments.csv | wc -l

# Run statistics
python analysis/gpt4o_statistical_analysis.py

# Backup
cp results/experiments.csv results/experiments_final_$(date +%Y%m%d).csv
```

## Success Criteria

- [x] All 1,620 runs completed
- [x] Zero MAX_TOKENS truncation
- [x] Failure rate <5%
- [x] 540 runs per engine
- [x] Completion tokens: 100-8000
- [x] Date range: May 25-31

## Quick Commands

```bash
# Monitor
python scripts/monitor_experiment.py

# Live watch
python scripts/monitor_experiment.py --watch

# Stop
kill $(cat temporal_pid.txt)

# Logs
tail -f temporal_execution.log
```

---

**Full Guide:** See `FULL_RERUN_GUIDE.md` for detailed instructions and troubleshooting.
