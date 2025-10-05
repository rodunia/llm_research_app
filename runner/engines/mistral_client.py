"""Mistral API client with retry and timeout handling."""

import os
import time
from typing import Dict, Any, Optional

from mistralai import Mistral
from mistralai.models import SDKError


def call_mistral(
    prompt: str,
    temperature: float,
    model: str = "mistral-small-latest",
    max_tokens: int = 2048,
    timeout: int = 60,
    max_retries: int = 3,
) -> Dict[str, Any]:
    """Call Mistral API with retry logic.

    Args:
        prompt: User prompt text
        temperature: Sampling temperature (0.0-1.0)
        model: Model identifier (default: mistral-small-latest)
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
        SDKError: If all retries fail
    """
    client = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))

    for attempt in range(max_retries):
        try:
            response = client.chat.complete(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
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

        except SDKError as e:
            # Check if it's a rate limit (429) or timeout
            if hasattr(e, "status_code"):
                if e.status_code == 429 and attempt < max_retries - 1:
                    wait_time = 2**attempt
                    time.sleep(wait_time)
                    continue
                elif e.status_code == 504 and attempt < max_retries - 1:
                    # Gateway timeout
                    continue

            # Non-retryable or final attempt
            raise

    raise SDKError("Max retries exceeded")
