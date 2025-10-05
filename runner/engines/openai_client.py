"""OpenAI API client with retry and timeout handling."""

import os
import time
from typing import Dict, Any, Optional

from openai import OpenAI, APIError, APITimeoutError, RateLimitError


def call_openai(
    prompt: str,
    temperature: float,
    model: str = "gpt-4o-mini",
    max_tokens: int = 2048,
    timeout: int = 60,
    max_retries: int = 3,
) -> Dict[str, Any]:
    """Call OpenAI API with retry logic.

    Args:
        prompt: User prompt text
        temperature: Sampling temperature (0.0-2.0)
        model: Model identifier (default: gpt-4o-mini)
        max_tokens: Maximum completion tokens
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

    Raises:
        APIError: If all retries fail
    """
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), timeout=timeout)

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_completion_tokens=max_tokens,
            )

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
