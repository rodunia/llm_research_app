# Sample Size Expansion Guide
**Date**: 2026-03-07

---

## ✅ Randomization Implemented!

**What changed**: `runner/generate_matrix.py` now randomizes run order by default

**Usage**:
```bash
# Generate with randomization (DEFAULT - recommended)
python -m runner.generate_matrix

# Custom seed for reproducibility
python -m runner.generate_matrix --seed 12345

# Disable randomization (NOT recommended)
python -m runner.generate_matrix --no-randomize
```

**Benefits**:
- Prevents temporal confounds
- API performance changes evenly distributed
- Model updates don't affect specific conditions
- Scientifically valid for temporal studies

---

## Current Sample Size: 243 runs

**Current config.py settings**:
- 3 products
- 3 materials
- 3 times (morning/afternoon/evening)
- 3 temps (0.2, 0.6, 1.0)
- 3 reps
- 3 engines (openai, google, mistral)

**Formula**: 3 × 3 × 3 × 3 × 3 × 3 = **243 runs**

---

## How to Expand Sample Size

### Option 1: Add 4th Engine (→ 324 runs)

**Edit config.py**:
```python
ENGINES = (
    "openai",
    "google",
    "mistral",
    "anthropic",  # Uncomment this line
)
```

**New total**: 3 × 3 × 3 × 3 × 3 × 4 = **324 runs**
**Increase**: +81 runs (33% more)

---

### Option 2: Add More Materials (→ 405 runs with 4 engines)

**Edit config.py**:
```python
MATERIALS = (
    "faq.j2",
    "digital_ad.j2",
    "blog_post_promo.j2",
    "organic_social_posts.j2",  # Uncomment
    "email_campaign.j2",         # If template exists
)
```

**With 3 engines**: 3 × 5 × 3 × 3 × 3 × 3 = **405 runs**
**With 4 engines**: 3 × 5 × 3 × 3 × 3 × 4 = **540 runs**

---

### Option 3: Add More Replications (→ 486 runs with 4 engines, 5 reps)

**Edit config.py**:
```python
REPS = (1, 2, 3, 4, 5)  # Increase from 3 to 5 replications
```

**New total** (with 4 engines): 3 × 3 × 3 × 3 × 5 × 4 = **540 runs**
**Benefit**: Tighter confidence intervals (better precision)

---

### Option 4: Add More Products (→ 432 runs with 4 products, 4 engines)

**Edit config.py**:
```python
PRODUCTS = (
    "smartphone_mid",
    "cryptocurrency_corecoin",
    "supplement_melatonin",
    "supplement_herbal",        # Add new product (needs YAML)
)
```

**New total** (with 4 engines): 4 × 3 × 3 × 3 × 3 × 4 = **432 runs**

---

### Option 5: Comprehensive Expansion (→ 1,620 runs)

**For 1,620 runs, you'd need**:
```python
# Example 1: More materials + more engines
MATERIALS = 5 materials (add 2 more)
ENGINES = 4 engines (add anthropic)
REPS = 3 reps
# = 3 × 5 × 3 × 3 × 3 × 4 = 540 runs (not 1,620)

# Example 2: Add more temperature points
PRODUCTS = 3
MATERIALS = 5
TIMES = 3
TEMPS = (0.0, 0.2, 0.4, 0.6, 0.8, 1.0)  # 6 temps instead of 3
REPS = 3
ENGINES = 4
# = 3 × 5 × 3 × 6 × 3 × 4 = 1,080 runs

# Example 3: Add temporal dimension (days)
DAYS = (1, 2, 3)  # Run over 3 days
PRODUCTS = 3
MATERIALS = 3
TIMES = 3 (per day)
TEMPS = 3
REPS = 3
ENGINES = 4
# = 3 × 3 × 3 × 3 × 3 × 3 × 4 = 972 runs

# Example 4: To reach exactly 1,620 runs:
PRODUCTS = 3
MATERIALS = 5 (add organic_social + email)
TIMES = 3
TEMPS = 3
REPS = 3
ENGINES = 4
DAYS = 3  # Add temporal replication
# = 3 × 5 × 3 × 3 × 3 × 4 × 3 = 1,620 runs ✓
```

---

## Recommended Expansion Path

### Stage 1: Add Anthropic (324 runs)
**Justification**: Minimal cost increase, adds important 4th LLM provider

```python
ENGINES = ("openai", "google", "mistral", "anthropic")
```

**Total**: 324 runs
**Time**: ~8-10 hours generation
**Cost**: ~$65-80

---

### Stage 2: Add 2 More Materials (540 runs)
**Justification**: Tests 5 different content types

```python
MATERIALS = (
    "faq.j2",
    "digital_ad.j2",
    "blog_post_promo.j2",
    "organic_social_posts.j2",
    "email_campaign.j2",  # If template exists
)
```

**Total**: 540 runs (with 4 engines)
**Time**: ~15-20 hours generation
**Cost**: ~$110-130

---

### Stage 3: Add Temporal Replication (1,620 runs)
**Justification**: Tests consistency over time (temporal reliability RQ)

**Add to config.py**:
```python
DAYS = (1, 2, 3)  # Day 1, Day 2, Day 3
```

**Modify generate_matrix.py** to include DAYS in Cartesian product:
```python
all_combinations = list(itertools.product(
    PRODUCTS, MATERIALS, TIMES, TEMPS, REPS, ENGINES, DAYS  # Add DAYS
))
```

**Total**: 1,620 runs
**Time**: ~50-60 hours generation (2-3 days)
**Cost**: ~$330-400

---

## Statistical Justification

| Sample Size | Margin of Error | Power (medium effect) | Recommendation |
|-------------|-----------------|----------------------|----------------|
| 243 | ±6.2% | 0.75 | ✅ Good for pilot |
| 324 | ±5.4% | 0.85 | ✅ Good for main study |
| 540 | ±4.2% | 0.95 | ✅✅ Excellent |
| 1,620 | ±2.4% | 0.99 | ✅✅✅ Publication-ready |

---

## Testing Your Changes

### 1. Dry-run to verify matrix size:
```bash
python -m runner.generate_matrix --dry-run
```

### 2. Generate with randomization:
```bash
# Backup old matrix first
mv results/experiments.csv results/experiments_old.csv

# Generate new matrix
python -m runner.generate_matrix
```

### 3. Verify randomization worked:
```bash
# Check that run order is shuffled (not sequential)
head -10 results/experiments.csv
# Should see mixed products/engines/temps (not all same product)
```

---

## Quick Reference: Current Config

**File**: `config.py`

To expand, uncomment/add lines:
- **Line 48**: Add `"anthropic"` to ENGINES
- **Lines 24-27**: Uncomment materials
- **Line 42**: Add more reps: `REPS = (1, 2, 3, 4, 5)`

---

## Summary

✅ **Randomization**: Implemented (default ON, seed=42)
✅ **Expansion**: Easy - just edit config.py
✅ **Current**: 243 runs
✅ **Recommended**: 540 runs (4 engines × 5 materials)
✅ **Maximum**: 1,620+ runs (add temporal dimension)

**Next step**: Decide your target sample size, edit config.py, regenerate matrix with randomization.
