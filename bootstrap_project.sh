#!/bin/sh
# bootstrap_project.sh
# Bootstraps an experiment repository with required directory structure and constants

set -eu

# --- DIRECTORY CREATION ---
# Create all required directories (idempotent with mkdir -p)
echo "Creating directory structure..."

mkdir -p products
mkdir -p prompts
mkdir -p runner
mkdir -p outputs
mkdir -p results
mkdir -p analysis
mkdir -p validation
mkdir -p lexicons
mkdir -p docs

# --- CONSTANTS DOCUMENT GENERATION ---
# Write experiment constants to docs/experiment_constants.md
echo "Writing experiment constants documentation..."

# Get current date for change control
TODAY=$(date +%Y-%m-%d)

# Use heredoc to write the constants file
cat > docs/experiment_constants.md <<EOF
# Experiment Constants

This document defines all constant values used across the experimental framework.

## Purpose

These constants ensure reproducibility and consistency across all experimental runs. Do not modify these values during an active experiment cycle.

## Product Constants

Products under test:
* \`supplement_melatonin\`
* \`smartphone\`
* \`cryptocurrency\`

## Material Type Templates

Template filenames for content generation:
* \`digital_ad.j2\`
* \`organic_social_posts.j2\`
* \`faq.j2\`
* \`spec_document_facts_only.j2\`
* \`blog_post_promo.j2\`

## Time of Day Constants

Experimental time periods:
* \`morning\`
* \`afternoon\`
* \`evening\`

## Temperature Settings

Model temperature parameters:
* \`0.2\` (low - more deterministic)
* \`0.6\` (medium - balanced)
* \`1.0\` (high - more creative)

## Repetition Constants

Number of repetitions per condition:
* \`1\`
* \`2\`
* \`3\`

## Engine Constants

LLM providers:
* \`openai\`
* \`google\`
* \`anthropic\`

## Regional Settings

Target region:
* \`US\`

## Feature Flags

Trap detection flag (default):
* \`false\`

## Change Control

**Last updated:** ${TODAY}

All changes to these constants must be documented and versioned.
EOF

# Verify file was written successfully
if [ ! -f docs/experiment_constants.md ]; then
    echo "ERROR: Failed to write docs/experiment_constants.md" >&2
    exit 1
fi

# --- SUMMARY OUTPUT ---
echo ""
echo "=========================================="
echo "Bootstrap Complete"
echo "=========================================="
echo "Created/verified 9 directories"
echo "Wrote docs/experiment_constants.md"
echo ""
echo "Current working directory:"
pwd
echo ""
echo "Created structure:"
find products prompts runner outputs results analysis validation lexicons docs -type d -o -name "experiment_constants.md" 2>/dev/null | sort
echo ""
echo "Bootstrap successful!"
