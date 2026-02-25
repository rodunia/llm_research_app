# config.py
# This file serves as the central configuration dashboard for the research app.
# All experimental parameters, prompts, models, and users are defined here.

# --- 1. EXPERIMENT CONSTANTS ---
# Current Setup (2025-01-15):
# - 3 products × 3 materials × 3 temps × 3 runs/day × 3 engines = 243 runs per day
# - Single user (no multi-user for now)
# - Materials: FAQ, Digital Ads, Blog Post Promos only
# - Runs 3 times per day (morning, afternoon, evening)

PRODUCTS = (
    "smartphone_mid",
    "cryptocurrency_corecoin",
    "supplement_melatonin",
    # Future products (create YAMLs when ready):
    # "supplement_herbal",
    # "audio_bt_headphones",
)

MATERIALS = (
    "faq.j2",
    "digital_ad.j2",
    "blog_post_promo.j2",
    # Excluded from current usage:
    # "organic_social_posts.j2",
    # "spec_document_facts_only.j2",
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

REPS = (1, 2, 3)  # Three runs per day (morning/afternoon/evening)

ENGINES = (
    "openai",
    "google",
    "mistral",
    # "anthropic",  # Excluded per research protocol
)

# Engine-to-model mapping (used by runner/engines/)
ENGINE_MODELS = {
    "openai": "gpt-4o",  # Upgraded from gpt-4o-mini to full gpt-4o
    "google": "gemini-2.0-flash-exp",  # Using 2.0 experimental (more permissive)
    "mistral": "mistral-large-2407",  # Large model (July 2024) - better quality for research
    "anthropic": "claude-3-opus-20240229",  # Claude 3 Opus (your API key tier)
}

REGION = "US"

# --- 2. METADATA AND REPRODUCIBILITY SETTINGS ---

# Default values for metadata tracking (statistical validity)
DEFAULT_MAX_TOKENS = 2000           # Max completion tokens
DEFAULT_SEED = 12345                # Fixed seed for reproducibility
DEFAULT_TOP_P = None                # Use API default (1.0), set to float to override
DEFAULT_FREQUENCY_PENALTY = None    # Use API default (0.0), set to float to override
DEFAULT_PRESENCE_PENALTY = None     # Use API default (0.0), set to float to override

# Session tracking
DEFAULT_SESSION_ID = "main_experiment"  # Can be overridden via CLI --session-id

# --- 3. USER ACCOUNTS ---
# Single user setup for current research
USER_ACCOUNTS = [
    "researcher_primary",  # Single user for now
]

# Default account for experiments
DEFAULT_ACCOUNT_ID = USER_ACCOUNTS[0]

# --- 3. LEGACY CONFIGURATIONS (ARCHIVED) ---
# NOTE: MODEL_CONFIGURATIONS, STANDARDIZED_PROMPTS, and get_model_config()
# were moved to archive/legacy_config.py on 2025-10-06.
#
# These were used by the deprecated interactive CLI (archive/main.py).
# The batch system uses ENGINE_MODELS (above) and Jinja2 templates (prompts/*.j2) instead.
#
# If you need these for reference, see: archive/legacy_config.py
