# Model Configuration Review
## Current vs Recommended Models

**Date**: 2026-02-25
**Issue**: config.py doesn't match scale-up recommendations

---

## 🔴 Current Configuration (config.py)

```python
ENGINE_MODELS = {
    "openai": "gpt-4o",                      # ⚠️ Rolling version
    "google": "gemini-2.0-flash-exp",        # ⚠️ Experimental
    "mistral": "mistral-small-latest",       # ⚠️ Small + Rolling
}
```

**Problems**:
1. ❌ **Mistral Small**: Lower quality, we decided on **Large**
2. ❌ **Rolling versions**: Not reproducible (gpt-4o, mistral-small-latest)
3. ❌ **Experimental**: gemini-2.0-flash-exp may change

---

## ✅ Recommended Configuration (READY_FOR_SCALE_UP.md)

```python
ENGINE_MODELS = {
    "openai": "gpt-4o-2024-08-06",          # ✅ Stable snapshot
    "google": "gemini-1.5-pro-002",         # ✅ Production version
    "mistral": "mistral-large-2407",        # ✅ Large model (July 2024)
}
```

**Benefits**:
- ✅ Reproducible 5+ years from now
- ✅ Version-locked (no surprises)
- ✅ Better quality (mistral-large vs small)
- ✅ Peer-reviewable

---

## 📋 Reasoning

### 1. Why Mistral Large (not Small)?

**Your Question**: "I THINK WE WERE THINKING ABOUT MISTRAL LARGE?"

**Answer**: YES! From `READY_FOR_SCALE_UP.md` line 54:
> **Note:** Changed Mistral from "small" to "large" for better quality

**Reasoning**:
- Mistral Small: Good for simple tasks, lower quality
- **Mistral Large**: Better reasoning, more accurate (needed for complex marketing content)
- Research needs high-quality outputs to test error detection
- Cost difference justified by research quality

### 2. Why Gemini 2.0 Flash Experimental?

**Your Question**: "tell me the reason for gemini experimental"

**Answer**: From `config.py` line 54:
> Using 2.0 experimental (more permissive)

**Reasoning** (from `runner/engines/google_client.py`):
- **Problem**: Gemini 1.5 blocks cryptocurrency/supplement content (too strict safety filters)
- **Solution**: Gemini 2.0 Flash Experimental is "more permissive" for marketing content
- **Safety settings**: Set to `BLOCK_NONE` for all categories

**Why it matters**:
- ✅ Cryptocurrency marketing → financial claims → Gemini 1.5 refuses
- ✅ Supplement marketing → health claims → Gemini 1.5 blocks
- ✅ 2.0 Flash allows these to generate (needed for experiment)

**BUT**: READY_FOR_SCALE_UP.md recommends switching to stable version:
> "google": "gemini-1.5-pro-002"        # ✅ Production version

**Tradeoff**: Reproducibility (1.5 stable) vs Permissiveness (2.0 experimental)

---

## 🎯 Decision Matrix

### Option A: Use Recommended (Reproducible)

```python
ENGINE_MODELS = {
    "openai": "gpt-4o-2024-08-06",
    "google": "gemini-1.5-pro-002",         # May block crypto/supplement
    "mistral": "mistral-large-2407",
}
```

**Pros**:
- ✅ Fully reproducible
- ✅ Version-locked for peer review
- ✅ Mistral Large (better quality)

**Cons**:
- ⚠️ Gemini 1.5 Pro may refuse crypto/supplement content
- ⚠️ Need to test if safety filters block your prompts

### Option B: Keep Current + Fix Mistral

```python
ENGINE_MODELS = {
    "openai": "gpt-4o-2024-08-06",          # Fix: version lock
    "google": "gemini-2.0-flash-exp",       # Keep: more permissive
    "mistral": "mistral-large-2407",        # Fix: upgrade to large
}
```

**Pros**:
- ✅ Gemini 2.0 won't block content
- ✅ Mistral Large (better quality)
- ✅ OpenAI version-locked

**Cons**:
- ⚠️ Gemini 2.0 experimental may change
- ⚠️ Less reproducible in 5 years

### Option C: Test Gemini 1.5 Pro First

```python
# Test if Gemini 1.5 Pro works with safety settings
ENGINE_MODELS = {
    "openai": "gpt-4o-2024-08-06",
    "google": "gemini-1.5-pro-002",         # Test this first
    "mistral": "mistral-large-2407",
}
```

**If Gemini 1.5 Pro blocks content** → switch to Option B
**If Gemini 1.5 Pro works** → use Option A

---

## 🔬 Testing Recommendation

Before scaling up to 1,620 runs, **test each model** on your 3 products:

```bash
# Test OpenAI (should work)
python -m runner.run_job single <smartphone_run_id>

# Test Mistral Large (should work)
python -m runner.run_job single <smartphone_run_id_mistral>

# Test Gemini 1.5 Pro with BLOCK_NONE settings
python -m runner.run_job single <cryptocurrency_run_id_google>
python -m runner.run_job single <supplement_run_id_google>

# Check if Gemini blocks content
grep "BLOCKED\|SAFETY" outputs/*.txt
```

**If Gemini 1.5 blocks**: Use `gemini-2.0-flash-exp` (Option B)
**If Gemini 1.5 works**: Use version-locked models (Option A)

---

## 📝 Recommended Actions

### Immediate: Fix Mistral (Definitely)

```python
# In config.py line 55, change:
"mistral": "mistral-small-latest",  # ❌ OLD

# To:
"mistral": "mistral-large-2407",    # ✅ NEW
```

**Why**: We explicitly decided on Large for better quality (READY_FOR_SCALE_UP.md)

### Test: Gemini 1.5 Pro vs 2.0 Flash

**Test Gemini 1.5 Pro first** (more reproducible):
```python
"google": "gemini-1.5-pro-002",
```

**If it blocks crypto/supplement** → switch to:
```python
"google": "gemini-2.0-flash-exp",  # More permissive
```

### Optional: Version-Lock OpenAI

```python
# Change:
"openai": "gpt-4o",                 # ❌ Rolling

# To:
"openai": "gpt-4o-2024-08-06",      # ✅ Stable
```

**Why**: Reproducibility for academic publication

---

## 🎓 Academic Reproducibility

**For your methods section**:

### Good (Current):
> "We used GPT-4o, Gemini 2.0 Flash, and Mistral Small"

**Problem**: Not reproducible (rolling versions change)

### Better (Recommended):
> "We used GPT-4o snapshot 2024-08-06, Gemini 1.5 Pro v002, and Mistral Large 2407"

**Benefit**: Someone can reproduce your exact experiment in 2030

---

## 💰 Cost Comparison

| Model | Old | New | Cost Impact |
|-------|-----|-----|-------------|
| OpenAI | gpt-4o | gpt-4o-2024-08-06 | Same (just version-locked) |
| Google | gemini-2.0-flash-exp | gemini-1.5-pro-002 | ~2x more expensive |
| Mistral | mistral-small-latest | mistral-large-2407 | ~3x more expensive |

**Total impact**: ~2.5x cost increase for Google + Mistral

**Trade-off**: Higher cost vs better quality + reproducibility

---

## 🎯 My Recommendation

**Start with this** (balanced approach):

```python
ENGINE_MODELS = {
    "openai": "gpt-4o-2024-08-06",          # Version-locked
    "google": "gemini-2.0-flash-exp",       # Keep for permissiveness
    "mistral": "mistral-large-2407",        # Upgrade to Large
}
```

**Why**:
1. ✅ Fixes Mistral (Large > Small) - **you explicitly wanted this**
2. ✅ Keeps Gemini 2.0 (won't block crypto/supplement)
3. ✅ Version-locks OpenAI (reproducible)
4. ✅ Can run full experiment without content blocking
5. ⚠️ Only Gemini is experimental (1/3 models)

**After experiment**: Document in paper that Gemini 2.0 was used for permissiveness, with caveat about experimental status.

---

## 📌 Summary

**Your Questions**:
1. ✅ **Mistral Large**: YES, we decided on Large (READY_FOR_SCALE_UP.md line 54)
2. ✅ **Gemini Experimental**: Used because it's "more permissive" - doesn't block crypto/supplement content

**Current Issue**: config.py still has `mistral-small-latest` instead of `mistral-large-2407`

**Recommendation**: Change to mistral-large-2407 NOW, test Gemini 1.5 Pro (may need to keep 2.0-flash-exp)

---

**Next Step**: Update config.py and test on sample runs before scaling to 1,620 files
