# config.py
# This file serves as the central configuration dashboard for the research app.
# All experimental parameters, prompts, models, and users are defined here.

# --- 1. EXPERIMENT CONSTANTS ---
# Frozen matrix constants (see docs/experiment_constants.md)
# Current: 3 products → 1,215 runs (3 products × 5 materials × 3 temps × 3 reps × 3 times × 3 engines)
# Future: 5 products → 2,700 runs (5 products × 5 materials × 3 temps × 3 reps × 3 times × 4 engines)

PRODUCTS = (
    "smartphone_mid",
    "cryptocurrency_corecoin",
    "supplement_melatonin",
    # Future products (create YAMLs when ready):
    # "supplement_herbal",
    # "audio_bt_headphones",
)

MATERIALS = (
    "digital_ad.j2",
    "organic_social_posts.j2",
    "faq.j2",
    "spec_document_facts_only.j2",
    "blog_post_promo.j2",
)

TIMES = (
    "morning",
    "afternoon",
    "evening",
)

TEMPS = (
    0.2,  # low - more deterministic
    0.6,  # medium - balanced
    1.0,  # high - more creative
)

REPS = (1, 2, 3)  # Repetition indices (used as "day" labels)

ENGINES = (
    "openai",
    "google",
    "mistral",
    # "anthropic",  # Disabled
)

# Engine-to-model mapping (used by runner/engines/)
ENGINE_MODELS = {
    "openai": "gpt-4o",  # Upgraded from gpt-4o-mini to full gpt-4o
    "google": "gemini-2.0-flash-exp",  # Using 2.0 experimental (more permissive)
    "mistral": "mistral-small-latest",
    "anthropic": "claude-3-opus-20240229",  # Claude 3 Opus (your API key tier)
}

REGION = "US"

# --- 2. USER ACCOUNTS ---
# A list of researcher accounts to be used in the experiments.
USER_ACCOUNTS = [
    "account_1",
    "account_2",
    "account_3",
]

# --- 3. LEGACY CONFIGURATIONS (ARCHIVED) ---
# NOTE: MODEL_CONFIGURATIONS, STANDARDIZED_PROMPTS, and get_model_config()
# were moved to archive/legacy_config.py on 2025-10-06.
#
# These were used by the deprecated interactive CLI (archive/main.py).
# The batch system uses ENGINE_MODELS (above) and Jinja2 templates (prompts/*.j2) instead.
#
# If you need these for reference, see: archive/legacy_config.py
