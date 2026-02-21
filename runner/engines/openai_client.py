"""OpenAI API client with retry and timeout handling."""

import os
import time
from typing import Dict, Any, Optional

from openai import OpenAI, APIError, APITimeoutError, RateLimitError

from config import ENGINE_MODELS


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

    for attempt in range(max_retries):
        try:
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

            response = client.chat.completions.create(**params)

            # Extract response data
            message = response.choices[0].message
            usage = response.usage

            return {
                "output_text": message.content or "",
                "finish_reason": response.choices[0].finish_reason,
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens,
                "model": response.model,
                "model_version": response.model,  # OpenAI returns snapshot ID in model field
            }

        except RateLimitError as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                time.sleep(wait_time)
                continue
            raise

        except APITimeoutError as e:
            if attempt < max_retries - 1:
                continue
            raise

        except APIError as e:
            # Non-retryable errors
            raise

    raise APIError("Max retries exceeded")
