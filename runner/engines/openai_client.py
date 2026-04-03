"""OpenAI API client with retry and timeout handling."""

import os
import time
from typing import Dict, Any, Optional

from openai import OpenAI, APIError, APITimeoutError, RateLimitError
from dotenv import load_dotenv

from config import ENGINE_MODELS
from logging_config import setup_logging

# Load environment variables from .env file
load_dotenv()

# Setup module logger
logger = setup_logging(__name__, console=False)  # Log to files only (avoid console spam)


def call_openai(
    prompt: str,
    temperature: float,
    model: Optional[str] = None,
    max_tokens: int = 2048,
    seed: Optional[int] = None,
    top_p: Optional[float] = None,
    frequency_penalty: Optional[float] = None,
    presence_penalty: Optional[float] = None,
    timeout: int = 60,
    max_retries: int = 3,
) -> Dict[str, Any]:
    """Call OpenAI API with retry logic.

    Args:
        prompt: User prompt text
        temperature: Sampling temperature (0.0-2.0)
        model: Model identifier (default: from ENGINE_MODELS config)
        max_tokens: Maximum completion tokens
        seed: Random seed for reproducibility (OpenAI beta feature)
        top_p: Nucleus sampling parameter (0.0-1.0)
        frequency_penalty: Repetition penalty (-2.0 to 2.0)
        presence_penalty: Token diversity penalty (-2.0 to 2.0)
        timeout: Request timeout in seconds
        max_retries: Maximum retry attempts

    Returns:
        Dictionary with keys:
            - output_text: Generated text
            - finish_reason: Completion reason (stop, length, etc.)
            - prompt_tokens: Input token count
            - completion_tokens: Output token count
            - total_tokens: Total token count
            - model: Model used
            - model_version: Model snapshot ID (same as model for OpenAI)
            - retry_count: Number of retry attempts (0 = success on first try)
            - error_type: Error classification (none, rate_limit, timeout, api_error)
            - content_filter_triggered: Boolean, True if safety filter blocked output
            - api_latency_ms: Milliseconds from request to response

    Raises:
        APIError: If all retries fail
    """
    # Use config default if model not specified
    if model is None:
        model = ENGINE_MODELS["openai"]

    # Validate API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY environment variable not set. "
            "Add it to your .env file or set it in your environment."
        )

    client = OpenAI(api_key=api_key, timeout=timeout)

    # Log API call parameters
    logger.info(f"API call: model={model}, temp={temperature}, max_tokens={max_tokens}, seed={seed}")

    # Track retry metadata
    retry_count = 0
    error_type = "none"

    for attempt in range(max_retries):
        try:
            logger.debug(f"Attempt {attempt+1}/{max_retries}")

            # Build API parameters (only include non-None optional params)
            params = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "max_completion_tokens": max_tokens,
            }

            # Add optional parameters if specified
            if seed is not None:
                params["seed"] = seed
            if top_p is not None:
                params["top_p"] = top_p
            if frequency_penalty is not None:
                params["frequency_penalty"] = frequency_penalty
            if presence_penalty is not None:
                params["presence_penalty"] = presence_penalty

            # Measure API latency
            api_start = time.time()
            response = client.chat.completions.create(**params)
            api_latency_ms = int((time.time() - api_start) * 1000)

            # Extract response data
            message = response.choices[0].message
            usage = response.usage

            # Check if content filter was triggered
            content_filter_triggered = (
                response.choices[0].finish_reason == "content_filter"
            )

            # Log successful response
            logger.info(
                f"Success: {usage.total_tokens} tokens "
                f"(prompt={usage.prompt_tokens}, completion={usage.completion_tokens}), "
                f"finish_reason={response.choices[0].finish_reason}, "
                f"retries={retry_count}, latency={api_latency_ms}ms"
            )

            return {
                "output_text": message.content or "",
                "finish_reason": response.choices[0].finish_reason,
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens,
                "model": response.model,
                "model_version": response.model,  # OpenAI returns snapshot ID in model field
                # NEW: 3 metadata fields
                "retry_count": retry_count,
                "error_type": error_type,
                "content_filter_triggered": content_filter_triggered,
                "api_latency_ms": api_latency_ms,
            }

        except RateLimitError as e:
            retry_count += 1
            error_type = "rate_limit"
            wait_time = 2 ** attempt  # Exponential backoff
            logger.warning(
                f"Rate limit hit (attempt {attempt+1}/{max_retries}), "
                f"retrying in {wait_time}s: {e}"
            )
            if attempt < max_retries - 1:
                time.sleep(wait_time)
                continue
            logger.error("Max retries exceeded for rate limit")
            raise

        except APITimeoutError as e:
            retry_count += 1
            error_type = "timeout"
            logger.warning(f"API timeout (attempt {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                continue
            logger.error("Max retries exceeded for timeout")
            raise

        except APIError as e:
            retry_count += 1
            error_type = "api_error"
            # Non-retryable errors
            logger.error(f"API error (non-retryable): {e}")
            raise

    logger.error("Max retries exceeded")
    raise APIError("Max retries exceeded")
