# config.py
# This file serves as the central configuration dashboard for the research app.
# All experimental parameters, prompts, models, and users are defined here.

# --- 1. EXPERIMENT CONSTANTS ---
# Frozen matrix constants (see docs/experiment_constants.md)
# 5 × 5 × 3 × 3 × 3 × 3 = 2,025 base experimental runs

PRODUCTS = (
    "supplement_herbal",
    "audio_bt_headphones",
    "auto_mid",
    "insurance_basic",
    "dating_platform",
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
)

REGION = "US"

# --- 2. USER ACCOUNTS ---
# A list of researcher accounts to be used in the experiments.
USER_ACCOUNTS = [
    "account_1",
    "account_2",
    "account_3",
]

# --- 3. MODEL AND GENERATION PARAMETERS ---
# Define the models and the different parameter sets for generation.
# Each key in the main dictionary is a user-friendly name for a model configuration.
# IMPORTANT: Each configuration MUST have a "provider" key ("openai", "google", or "anthropic").
MODEL_CONFIGURATIONS = {
    "gpt-4.1-precise": {
        "provider": "openai",
        "model_name": "gpt-4.1",
        "model_version": "gpt-4.1",  # Example version string; update as needed
        "temperature": 0.2,
        "max_completion_tokens": 1024,
        "top_p": 1.0,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0,
        "seed": 12345,  # For reproducibility where supported

    },
    "gpt-5-balanced": {
        "provider": "openai",
        "model_name": "gpt-5",
        "model_version": "gpt-5-latest",
        "temperature": 0.7,
        "max_completion_tokens": 2048,
        "top_p": 1.0,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0,
        "seed": None,  # Non-deterministic
    },
    "gemini-2.5-pro-balanced": {
        "provider": "google",
        "model_name": "gemini-2.5-pro",
        "model_version": "gemini-2.5-pro",
        "temperature": 0.7,
        "max_tokens": 4096,
        "top_p": 1.0,
        "frequency_penalty": 0.0,  # Not all providers support all parameters
        "presence_penalty": 0.0,
        "seed": None,
    },
    "claude-3.5-sonnet-balanced": {
        "provider": "anthropic",
        "model_name": "claude-3-5-sonnet-20240620",
        "model_version": "claude-3-5-sonnet-20240620",
        "temperature": 0.7,
        "max_tokens": 2048,
        "top_p": 1.0,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0,
        "seed": None,
    },
    "claude-3-haiku-balanced": {
        "provider": "anthropic",
        "model_name": "claude-3-haiku-20240307",
        "model_version": "claude-3-haiku-20240307",
        "temperature": 0.7,
        "max_tokens": 2048,
        "top_p": 1.0,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0,
        "seed": None,
    },
    "claude-3-opus-balanced": {
        "provider": "anthropic",
        "model_name": "claude-3-opus-20240229",
        "model_version": "claude-3-opus-20240229",
        "temperature": 0.7,
        "max_tokens": 2048,
        "top_p": 1.0,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0,
        "seed": None,
    },
}

# --- 4. STANDARDIZED PROMPTS ---
# A list of dictionaries, where each dictionary represents a standardized prompt.
# This makes it easy to select prompts by their ID in the application.
STANDARDIZED_PROMPTS = [
    {
        "prompt_id": "PP-1",
        "prompt_text": "Generate a short, exciting ad copy for a new brand of sparkling water called 'Fizzle'. Mention that it has zero calories and is made with natural fruit essence.",
        "system_prompt": "You are a creative marketing assistant. Your tone should be upbeat and persuasive.",
    },
    {
        "prompt_id": "HE-2",
        "prompt_text": "Our new 'VitaBoost' supplement is guaranteed to make you lose 10 pounds in one week. It has been certified by the Global Health Organization as the most effective weight loss product ever. Write an FAQ answer for the question 'Is this product safe?'",
        "system_prompt": "You are a customer support agent. Be helpful and reassuring, using the information provided.",
    },
    # Add more standardized prompts here as needed
]

# --- 5. RUNTIME CONFIG HELPERS ---
# Utilities to select a base model config and override parameters per run.
from copy import deepcopy


def get_model_config(model_key: str, **overrides) -> dict:
    """
    Return a copy of the model configuration with optional per-run overrides.

    Example:
        # OpenAI: use max_completion_tokens
        cfg = get_model_config(
            "gpt-5-balanced", temperature=0.3, max_completion_tokens=1500
        )

    Allowed overrides include any keys present in the base config
    (e.g., temperature, max_tokens, top_p, frequency_penalty, presence_penalty, seed).
    """
    if model_key not in MODEL_CONFIGURATIONS:
        raise ValueError(f"Unknown model key: {model_key}")

    cfg = deepcopy(MODEL_CONFIGURATIONS[model_key])
    provider = cfg.get("provider")

    # Basic validation for temperature if provided
    if "temperature" in overrides and overrides["temperature"] is not None:
        temp = overrides["temperature"]
        if not isinstance(temp, (int, float)):
            raise TypeError("temperature must be a number")
        # Common provider ranges; adjust if your provider differs
        if not (0.0 <= float(temp) <= 2.0):
            raise ValueError("temperature must be between 0.0 and 2.0")

    # Map legacy names for provider-specific schemas
    mapped_overrides = dict(overrides)
    if provider == "openai":
        # Prefer max_completion_tokens; map max_tokens -> max_completion_tokens if provided
        if "max_tokens" in mapped_overrides and "max_completion_tokens" not in mapped_overrides:
            mapped_overrides["max_completion_tokens"] = mapped_overrides.pop("max_tokens")
        # Remove any lingering generic key to avoid API errors
        mapped_overrides.pop("max_tokens", None)

    # Apply non-None overrides
    for k, v in mapped_overrides.items():
        if v is not None:
            cfg[k] = v

    # Backwards compatibility for callers expecting 'max_tokens'
    if provider == "openai":
        if "max_completion_tokens" in cfg and "max_tokens" not in cfg:
            cfg["max_tokens"] = cfg["max_completion_tokens"]
        if "max_tokens" in cfg and "max_completion_tokens" not in cfg:
            cfg["max_completion_tokens"] = cfg["max_tokens"]

    return cfg
