# Experiment Constants

This document defines all constant values used across the experimental framework.

**Current Matrix Size:** 3 products × 5 materials × 3 times × 3 temperatures × 3 repetitions × 3 engines = **1,215 runs**

**Future Matrix Size (when all products ready):** 5 × 5 × 3 × 3 × 3 × 3 = **2,025 runs**

## Purpose

Single source of truth for all experimental factors. These constants ensure reproducibility and consistency across all experimental runs. **Do not modify these values during an active experiment cycle.**

## Product Constants

**Active Products (3):**
* `smartphone`
* `cryptocurrency`
* `supplement_melatonin`

**Future Products (2) - YAML files to be created:**
* `supplement_herbal`
* `audio_bt_headphones`

## Material Type Templates (5)

Template filenames for content generation:
* `digital_ad.j2`
* `organic_social_posts.j2`
* `faq.j2`
* `spec_document_facts_only.j2`
* `blog_post_promo.j2`

## Time of Day Constants (3)

Experimental time periods:
* `morning`
* `afternoon`
* `evening`

## Temperature Settings (3)

Model temperature parameters:
* `0.2` (low - more deterministic)
* `0.6` (medium - balanced)
* `1.0` (high - more creative)

## Repetition Constants (3)

Repetition indices (used as "day" labels for temporal variability):
* `1`
* `2`
* `3`

## Engine Constants (3)

LLM providers/engines:
* `openai`
* `google`
* `mistral`

## Regional Settings

Target region:
* `US`

## Feature Flags

**Trap Flag (default):**
* `false`

Note: `trap_flag` can be toggled in bias runs but is **not** part of the 2,025 base matrix.

## Matrix Calculation

**Current:** 3 products × 5 materials × 3 times × 3 temperatures × 3 repetitions × 3 engines = **1,215 runs**

**Future (5 products):** 5 × 5 × 3 × 3 × 3 × 3 = **2,025 runs**

## Change Control

**Last updated:** 2025-10-05

All changes to these constants must be documented and versioned.
