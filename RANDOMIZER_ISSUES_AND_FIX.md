# Randomizer Issues and Comprehensive Fix

**Date**: 2026-03-25
**Status**: Issues identified, fix designed

---

## Issues Identified

### **Issue 1: Time Slot Counts Not Exactly 540/540/540**

**Current behavior**:
```
morning:   542 runs (expected: 540)
afternoon: 539 runs (expected: 540)
evening:   539 runs (expected: 540)
```

**Root cause**: Lines 279-286 in `test_randomizer_stratified.py`
```python
target_per_slot = len(day_runs) // 3  # = 231 // 3 = 77
remainder = len(day_runs) % 3         # = 231 % 3 = 0 (or 232 % 3 = 1)

balanced_slots = (
    ['morning'] * (target_per_slot + (1 if remainder > 0 else 0)) +  # Gets extra
    ['afternoon'] * (target_per_slot + (1 if remainder > 1 else 0)) + # Gets extra
    ['evening'] * target_per_slot  # Never gets extra
)
```

**Problem**: Within-day balancing creates perfect balance per day, but across 7 days:
- Days with 231 runs: 77/77/77 per slot
- Days with 232 runs: 78/77/77 per slot (morning gets +1)
- 3 days × 78 morning + 4 days × 77 morning = 234 + 308 = 542 ✗

**Why chi-square passes**: Deviation is only 0.37%, which is statistically insignificant but NOT mathematically perfect.

---

### **Issue 2: Unequal Hour Ranges**

**Current definitions** (lines 76-80):
```python
TIME_SLOTS = {
    'morning': (8, 12),    # 4 hours
    'afternoon': (12, 17),  # 5 hours
    'evening': (17, 22)     # 5 hours
}
```

**Problem**: Calls per hour are NOT equal across time slots:
```
morning:   542 / 4h = 135.5 calls/hour  ← 26% HIGHER than others
afternoon: 539 / 5h = 107.8 calls/hour
evening:   539 / 5h = 107.8 calls/hour
```

**Impact**:
- API rate limit risk in morning (135 calls/hour vs 108)
- Temporal confounding (morning has higher density)

---

### **Issue 3: Engines Have Different Time Slot Distributions**

**Current behavior**:
```
openai:   morning=181, afternoon=171, evening=188
google:   morning=171, afternoon=194, evening=175
mistral:  morning=190, afternoon=174, evening=176
```

**Root cause**: Engine balancing (lines 326-393) happens AFTER time slot assignment, using minimal swaps to fix imbalance. These swaps don't preserve time slot distribution.

**Why overall mean is equal**: All engines have 540 total runs, but distributed differently across time slots. Overall mean = 540 / 14 hours = 38.57 calls/hour (same for all).

**Problem**: Time-of-day confounding with engine:
- If morning has higher error rates, OpenAI/Mistral affected more than Google
- If afternoon API is slower, Google affected more
- ANOVA assumption violated: "no interaction between blocking factor and treatment"

---

## Comprehensive Fix

### **Fix 1: Global Time Slot Balancing**

**Strategy**: Balance time slots GLOBALLY (across all 1,620 runs), not per-day.

**Implementation**:
```python
# After generating all 1,620 runs (before engine balancing)
def balance_time_slots_globally(runs: List[Dict], seed: int) -> List[Dict]:
    """
    Ensure exactly 540 runs per time slot globally.

    Algorithm:
    1. Count current distribution
    2. Identify donors (over 540) and receivers (under 540)
    3. Randomly swap time slots to achieve perfect balance
    4. Regenerate timestamps for swapped runs
    """
    random.seed(seed + 1000)  # Different seed from main randomization

    # Count current distribution
    slot_counts = {'morning': 0, 'afternoon': 0, 'evening': 0}
    slot_indices = {'morning': [], 'afternoon': [], 'evening': []}

    for idx, run in enumerate(runs):
        slot = run['time_slot']
        slot_counts[slot] += 1
        slot_indices[slot].append(idx)

    print(f"\n📊 Time slot distribution BEFORE global balancing:")
    print(f"  morning:   {slot_counts['morning']} (target: 540)")
    print(f"  afternoon: {slot_counts['afternoon']} (target: 540)")
    print(f"  evening:   {slot_counts['evening']} (target: 540)")

    # Perform swaps to achieve 540/540/540
    target = 540
    swaps = 0

    while not all(count == target for count in slot_counts.values()):
        # Find donor (over 540) and receiver (under 540)
        donors = [s for s, c in slot_counts.items() if c > target]
        receivers = [s for s, c in slot_counts.items() if c < target]

        if not donors or not receivers:
            break

        donor_slot = donors[0]
        receiver_slot = receivers[0]

        # Pick random run from donor slot
        donor_idx = random.choice(slot_indices[donor_slot])

        # Swap time slot
        runs[donor_idx]['time_slot'] = receiver_slot

        # Regenerate timestamp for new slot
        day_idx = runs[donor_idx]['day_index']
        runs[donor_idx]['timestamp'] = generate_random_timestamp(day_idx, receiver_slot)

        # Update tracking
        slot_indices[donor_slot].remove(donor_idx)
        slot_indices[receiver_slot].append(donor_idx)
        slot_counts[donor_slot] -= 1
        slot_counts[receiver_slot] += 1
        swaps += 1

    print(f"\n✅ Time slot balancing complete ({swaps} swaps)")
    print(f"📊 Time slot distribution AFTER global balancing:")
    for slot in ['morning', 'afternoon', 'evening']:
        print(f"  {slot:10s}: {slot_counts[slot]} (target: 540)")

    return runs
```

---

### **Fix 2: Equal Hour Ranges**

**Option A: Change evening to 4 hours** (Recommended)
```python
TIME_SLOTS = {
    'morning': (8, 12),    # 4 hours (8am-12pm)
    'afternoon': (13, 18),  # 5 hours (1pm-6pm)
    'evening': (18, 22)     # 4 hours (6pm-10pm)
}
```
Result: 540/4 = 135, 540/5 = 108, 540/4 = 135 calls/hour

**Option B: Make all 5 hours**
```python
TIME_SLOTS = {
    'morning': (7, 12),    # 5 hours (7am-12pm)
    'afternoon': (12, 17),  # 5 hours (12pm-5pm)
    'evening': (17, 22)     # 5 hours (5pm-10pm)
}
```
Result: 540/5 = 108 calls/hour (PERFECTLY EQUAL)

**Option C: Make all 4 hours + late evening**
```python
TIME_SLOTS = {
    'morning': (8, 12),     # 4 hours
    'afternoon': (13, 17),   # 4 hours
    'evening': (18, 22),     # 4 hours
    'late_evening': (22, 2)  # 4 hours (overnight)
}
```
Result: 4 time slots × 405 runs = 1620, 405/4 = 101.25 calls/hour

**Recommendation**: **Option B** (5/5/5) for perfect uniformity

---

### **Fix 3: Engine × Time Slot Stratification**

**Strategy**: Ensure each engine has EXACTLY 180 runs per time slot (540/3 = 180).

**Implementation**:
```python
def balance_engines_within_time_slots(runs: List[Dict], seed: int) -> List[Dict]:
    """
    Ensure each engine has exactly 180 runs per time slot.

    Target distribution:
    - openai:   180 morning + 180 afternoon + 180 evening = 540
    - google:   180 morning + 180 afternoon + 180 evening = 540
    - mistral:  180 morning + 180 afternoon + 180 evening = 540
    """
    random.seed(seed + 2000)

    # Count current engine × time slot distribution
    counts = {
        (engine, slot): 0
        for engine in ENGINES
        for slot in ['morning', 'afternoon', 'evening']
    }

    indices = {key: [] for key in counts.keys()}

    for idx, run in enumerate(runs):
        key = (run['engine'], run['time_slot'])
        counts[key] += 1
        indices[key].append(idx)

    print(f"\n🔧 Engine × Time Slot distribution BEFORE balancing:")
    for engine in ENGINES:
        morning = counts[(engine, 'morning')]
        afternoon = counts[(engine, 'afternoon')]
        evening = counts[(engine, 'evening')]
        print(f"  {engine:10s}: morning={morning:3d}, afternoon={afternoon:3d}, evening={evening:3d}")

    # Perform swaps to achieve 180/180/180 for each engine
    target = 180
    swaps = 0

    # Strategy: For each time slot, balance engines
    for time_slot in ['morning', 'afternoon', 'evening']:
        slot_done = False

        while not slot_done:
            # Find donor and receiver engines for this time slot
            donors = [e for e in ENGINES if counts[(e, time_slot)] > target]
            receivers = [e for e in ENGINES if counts[(e, time_slot)] < target]

            if not donors or not receivers:
                slot_done = True
                break

            donor_engine = donors[0]
            receiver_engine = receivers[0]

            # Find a run from donor_engine in this time slot
            donor_candidates = [idx for idx in indices[(donor_engine, time_slot)]]

            # Find a run from receiver_engine in a DIFFERENT time slot
            other_slots = [s for s in ['morning', 'afternoon', 'evening'] if s != time_slot]
            receiver_candidates = []
            for other_slot in other_slots:
                if counts[(receiver_engine, other_slot)] > target:
                    receiver_candidates.extend(indices[(receiver_engine, other_slot)])

            if not donor_candidates or not receiver_candidates:
                slot_done = True
                break

            # Swap engines between two runs
            idx1 = random.choice(donor_candidates)
            idx2 = random.choice(receiver_candidates)

            # Swap engines
            old_slot1 = runs[idx1]['time_slot']
            old_slot2 = runs[idx2]['time_slot']

            runs[idx1]['engine'], runs[idx2]['engine'] = runs[idx2]['engine'], runs[idx1]['engine']

            # Update tracking
            indices[(donor_engine, old_slot1)].remove(idx1)
            indices[(receiver_engine, old_slot1)].append(idx1)
            indices[(receiver_engine, old_slot2)].remove(idx2)
            indices[(donor_engine, old_slot2)].append(idx2)

            counts[(donor_engine, old_slot1)] -= 1
            counts[(receiver_engine, old_slot1)] += 1
            counts[(receiver_engine, old_slot2)] -= 1
            counts[(donor_engine, old_slot2)] += 1

            swaps += 1

    print(f"\n✅ Engine × Time Slot balancing complete ({swaps} swaps)")
    print(f"🔧 Engine × Time Slot distribution AFTER balancing:")
    for engine in ENGINES:
        morning = counts[(engine, 'morning')]
        afternoon = counts[(engine, 'afternoon')]
        evening = counts[(engine, 'evening')]
        print(f"  {engine:10s}: morning={morning:3d}, afternoon={afternoon:3d}, evening={evening:3d}")

    return runs
```

---

## Implementation Order

1. **Fix 2 first**: Update `TIME_SLOTS` to equal hour ranges (5/5/5)
2. **Fix 1 second**: Add global time slot balancing function
3. **Fix 3 third**: Add engine × time slot stratification
4. **Update pipeline**: Call functions in order:
   ```python
   runs = create_stratified_matrix(seed=42)
   runs = balance_time_slots_globally(runs, seed=42)
   runs = balance_engines_within_time_slots(runs, seed=42)
   ```

---

## Verification Checklist

After implementing fixes, verify:

- [ ] Time slots: exactly 540/540/540
- [ ] Hour ranges: equal across all slots (108 calls/hour for 5/5/5)
- [ ] Engine × time slot: exactly 180 for all 9 combinations
- [ ] Engine totals: still 540/540/540
- [ ] Day totals: still 231-232 per day
- [ ] Total runs: still 1620
- [ ] No run_id collisions
- [ ] Chi-square tests pass for all dimensions

---

## Expected Final Distribution

```
Time slots:
  morning:   540 runs / 5h = 108.0 calls/hour
  afternoon: 540 runs / 5h = 108.0 calls/hour
  evening:   540 runs / 5h = 108.0 calls/hour

Engines (per time slot):
  openai:   180 morning + 180 afternoon + 180 evening = 540
  google:   180 morning + 180 afternoon + 180 evening = 540
  mistral:  180 morning + 180 afternoon + 180 evening = 540

Mean calls/hour (per engine):
  openai:   540 / 15h = 36.0 calls/hour
  google:   540 / 15h = 36.0 calls/hour
  mistral:  540 / 15h = 36.0 calls/hour
```

**Perfect uniformity achieved!**
