# Ground Truth: Intentional Errors in Pilot Study (30 Files)

## Melatonin Supplement - 10 Intentional Errors

| File | Error Description | Error Type | AI Motivation |
|------|-------------------|------------|---------------|
| user_melatonin_1 | Dosage error (e.g., mg/tablet mismatch, serving-size mismatch, unit confusion) | Numerical hallucination | AI may confuse dosage units or serving sizes |
| user_melatonin_2 | Bottle count changed from 120 → 100 tablets | Factual inconsistency | AI may default to common supplement sizes (30, 60, 90, 100) |
| user_melatonin_3 | Claims vegan product contains fish-derived ingredients | Logical contradiction | AI may blend contradictory info when merging sources |
| user_melatonin_4 | Adds wheat traces despite "0 mg gluten" specification | Domain misunderstanding | AI may confuse gluten-free vs. wheat-free |
| user_melatonin_5 | Lead limit changed (decimal misplacement) | Decimal misplacement | AI may drop decimal points or simplify numbers |
| user_melatonin_6 | Recommends storage at 0°C | Over-literal interpretation | AI may assume "cool storage" literally means freezing |
| user_melatonin_7 | Suggests taking melatonin every 2 hours | Unsafe dosage hallucination | AI may generalize dosage patterns from unrelated medications |
| user_melatonin_8 | Claims FDA approval for supplement | Regulatory misunderstanding | AI often incorrectly assumes supplements are FDA-approved |
| user_melatonin_9 | Says avoid use if over 18 (age reversal) | Reversal error | AI may invert age restrictions (should be "under 18") |
| user_melatonin_10 | Claims permanent drowsiness side effect | Overgeneralization / hallucinated risk | AI may exaggerate side effects when uncertain |

---

## Smartphone (Mid-Range) - 10 Intentional Errors

| File | Error Description | Error Type | AI Motivation |
|------|-------------------|------------|---------------|
| user_smartphone_1 | Display size changed from 6.3" → 6.5" | Numerical drift | AI often "rounds up" or defaults to common display sizes |
| user_smartphone_2 | Camera changed from 50 MP → 48 MP | Spec substitution | AI substitutes familiar spec from other phones |
| user_smartphone_3 | Adds 1 TB storage option (not available) | Hallucinated feature | AI assumes modern phones always include 1 TB tier |
| user_smartphone_4 | Adds 16 GB RAM option (not available) | Overgeneralization | AI generalizes from flagship trend |
| user_smartphone_5 | Wi-Fi 6/6E → Wi-Fi 7 | Future spec hallucination | AI assumes newest standard applies |
| user_smartphone_6 | Claims wireless charging support (not supported) | Assumption error | AI fills gaps with "expected" features |
| user_smartphone_7 | Adds hourly antivirus scanning | Misattributed capability | AI confuses Android OS features with device-specific ones |
| user_smartphone_8 | Claims offline AI video rendering | Capability exaggeration | AI overextends AI capabilities |
| user_smartphone_9 | Fast charging changed from 30-45W → 60W | Numerical inflation | AI inflates charging wattage |
| user_smartphone_10 | Claims external SSD support via SIM tray | Hardware impossibility | AI invents impossible hardware behavior |

---

## CoreCoin Cryptocurrency - 10 Intentional Errors

| File | Error Description | Error Type | AI Motivation |
|------|-------------------|------------|---------------|
| user_corecoin_1 | Block time changed from ~5s → 4s | Numerical drift | AI may simplify or round technical specs |
| user_corecoin_2 | Claims support for non-staking light validators | Consensus misunderstanding | AI may confuse validator types across different blockchains |
| user_corecoin_3 | Claims regional trading pauses during maintenance | Domain transfer error | AI may transfer stock exchange concepts to crypto |
| user_corecoin_4 | Claims automatic key sharding for backup | Feature hallucination | AI may invent convenience features that don't exist |
| user_corecoin_5 | Claims gas-free smart contract execution | Technical impossibility | AI may assume "low fees" means "no fees" |
| user_corecoin_6 | Claims governance proposals auto-pass without quorum | Governance logic error | AI may misunderstand quorum requirements |
| user_corecoin_7 | Claims RPC layer can simulate cross-chain calls | Architecture confusion | AI may overstate cross-chain capabilities |
| user_corecoin_8 | Claims unstaking reduces historical reward rates | Reward model hallucination | AI may incorrectly apply penalty logic |
| user_corecoin_9 | Claims validator inactivity locks governance rights | Protocol overextension | AI may confuse staking penalties with governance restrictions |
| user_corecoin_10 | Claims region-based staking reward tiers | Regulatory fabrication | AI may incorrectly apply geographic restrictions |

---

## Error Type Taxonomy

### Numerical Errors (7 total)
- **Numerical drift:** Rounding or simplifying numbers (corecoin_1, smartphone_1)
- **Numerical hallucination:** Unit confusion, dosage errors (melatonin_1)
- **Decimal misplacement:** Dropping decimals (melatonin_5)
- **Numerical inflation:** Exaggerating specs (smartphone_9)
- **Spec substitution:** Swapping familiar numbers (smartphone_2)

### Feature Hallucinations (8 total)
- **Hallucinated feature:** Adding non-existent features (smartphone_3, smartphone_6, corecoin_4)
- **Capability exaggeration:** Overstating abilities (smartphone_8, corecoin_7)
- **Future spec hallucination:** Assuming newest standards (smartphone_5)
- **Hardware impossibility:** Inventing impossible behavior (smartphone_10)
- **Unsafe dosage hallucination:** Dangerous recommendations (melatonin_7)

### Logical/Domain Errors (9 total)
- **Logical contradiction:** Internal inconsistency (melatonin_3)
- **Domain misunderstanding:** Confusing related concepts (melatonin_4, corecoin_2)
- **Domain transfer error:** Applying concepts from wrong domain (corecoin_3)
- **Misattributed capability:** Confusing system vs device features (smartphone_7)
- **Consensus misunderstanding:** Blockchain-specific confusion (corecoin_2)
- **Governance logic error:** Protocol misunderstanding (corecoin_6)
- **Architecture confusion:** Overstatement of capabilities (corecoin_7)
- **Protocol overextension:** Incorrect penalty logic (corecoin_9)

### Factual Errors (6 total)
- **Factual inconsistency:** Changing documented facts (melatonin_2)
- **Reversal error:** Inverting conditions (melatonin_9)
- **Overgeneralization:** Applying trends incorrectly (smartphone_4, melatonin_10, corecoin_10)
- **Assumption error:** Filling gaps with assumptions (smartphone_6)
- **Over-literal interpretation:** Misunderstanding language (melatonin_6)
- **Regulatory misunderstanding:** Incorrect legal claims (melatonin_8)

---

## Keywords for Detection

### Melatonin Error Keywords

```python
MELATONIN_KEYWORDS = {
    1: ['mg', 'dosage', 'tablet', 'serving', 'mcg', 'milligram'],
    2: ['120', '100', 'bottle', 'count', 'tablets'],
    3: ['vegan', 'fish', 'gelatin', 'fish-derived', 'fish oil'],
    4: ['wheat', 'gluten', 'traces', 'gluten-free'],
    5: ['lead', 'mcg', 'ppb', 'heavy metal', '10 mcg', '0.01'],
    6: ['0°C', 'zero degrees', 'freezing', 'freeze', 'refrigerate'],
    7: ['every 2 hours', 'hourly', 'frequent', 'multiple times'],
    8: ['FDA approved', 'FDA approval', 'FDA-approved'],
    9: ['over 18', 'above 18', 'adults only', 'age restriction'],
    10: ['permanent', 'drowsiness', 'forever', 'irreversible']
}
```

### Smartphone Error Keywords

```python
SMARTPHONE_KEYWORDS = {
    1: ['6.5', '6.5"', '6.5-inch', 'display'],
    2: ['48 MP', '48MP', '48-megapixel'],
    3: ['1 TB', '1TB', 'terabyte', '1024 GB'],
    4: ['16 GB RAM', '16GB RAM', '16 GB memory'],
    5: ['Wi-Fi 7', 'WiFi 7', '802.11be'],
    6: ['wireless charging', 'Qi charging', 'wireless charge'],
    7: ['hourly', 'antivirus scan', 'every hour', 'scheduled scan'],
    8: ['offline AI', 'offline video rendering', 'on-device rendering'],
    9: ['60W', '60 watt', '60-watt'],
    10: ['SIM tray', 'external SSD', 'SSD via SIM', 'storage expansion SIM']
}
```

### CoreCoin Error Keywords

```python
CORECOIN_KEYWORDS = {
    1: ['4 second', '4s', '4-second', 'block time'],
    2: ['light validator', 'light-validator', 'non-staking validator'],
    3: ['regional pause', 'trading pause', 'maintenance window', 'regional trading'],
    4: ['automatic', 'key sharding', 'key-sharding', 'auto-shard'],
    5: ['gas-free', 'without gas', 'zero gas', 'no gas fee'],
    6: ['auto-pass', 'automatically pass', 'without quorum'],
    7: ['RPC', 'cross-chain', 'simulate', 'cross-chain call'],
    8: ['unstaking', 'reduce', 'historical reward', 'penalty'],
    9: ['inactivity', 'lock', 'governance', 'voting rights'],
    10: ['region-based', 'regional', 'staking tier', 'geographic']
}
```

---

## Expected Detection Challenges

### Melatonin
- **Regulatory claims** (File 8): May require specific prohibited_claims for FDA approval
- **Dosage reversal** (File 9): Negations challenging for NLI
- **Vegan contradiction** (File 3): Requires understanding product category

### Smartphone
- **Numerical drift** (Files 1, 2, 9): Close numbers (6.3→6.5, 48→50) may not trigger high contradiction
- **Future specs** (File 5): Wi-Fi 7 vs Wi-Fi 6 requires version awareness
- **Hardware impossibility** (File 10): Novel claim may not have explicit prohibition

### CoreCoin
- **Compound claims** (File 3): "Regional trading pauses" embedded in longer sentence
- **NLI confusion** (Files 2, 7, 9): Technical terms semantically grouped incorrectly
- **Decimal precision** (File 1): 4s vs ~5s requires numerical understanding

---

## Success Metrics

For each product, we will measure:

1. **Detection Rate** = (errors detected / total intentional errors) × 100%
   - Target: ≥70% (validated with CoreCoin at 67%)

2. **Correct Rule Matching Rate** = (correct rules / detected errors) × 100%
   - Target: ≥60% (achieved 67% with CoreCoin after optimization)

3. **False Positive Rate** = (false positives / total violations) × 100%
   - Baseline: 94-97% across products
   - Goal: Document, not eliminate (FP review is expected workflow)

4. **High-Confidence Correct Matches** = count of errors matched with ≥97% confidence
   - CoreCoin achieved: 4/6 detected errors at 97-99% confidence
   - Target: ≥3 per product
