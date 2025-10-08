"""Anthropic Claude API client with retry and timeout handling."""

import os
import time
from typing import Dict, Any, Optional

import anthropic
from anthropic import APIError, APITimeoutError, RateLimitError

from config import ENGINE_MODELS


def call_anthropic(
    prompt: str,
    temperature: float,
    model: Optional[str] = None,
    max_tokens: int = 2048,
    timeout: int = 60,
    max_retries: int = 3,
) -> Dict[str, Any]:
    """Call Anthropic Claude API with retry logic.

    Args:
        prompt: User prompt text
        temperature: Sampling temperature (0.0-1.0)
        model: Model identifier (default: from ENGINE_MODELS config)
        max_tokens: Maximum completion tokens
        timeout: Request timeout in seconds
        max_retries: Maximum retry attempts

    Returns:
        Dictionary with keys:
            - output_text: Generated text
            - finish_reason: Completion reason (end_turn, max_tokens, etc.)
            - prompt_tokens: Input token count
            - completion_tokens: Output token count
            - total_tokens: Total token count
            - model: Model used

    Raises:
        APIError: If all retries fail
    """
    # Use config default if model not specified
    if model is None:
        model = ENGINE_MODELS["anthropic"]

    # Validate API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError(
            "ANTHROPIC_API_KEY environment variable not set. "
            "Add it to your .env file or set it in your environment."
        )

    client = anthropic.Anthropic(
        api_key=api_key,
        timeout=timeout
    )

    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}],
            )

            # Extract text content from response
            output_parts = []
            for block in response.content:
                if hasattr(block, "text"):
                    output_parts.append(block.text)
                elif isinstance(block, dict) and "text" in block:
                    output_parts.append(block["text"])

            output_text = "".join(output_parts)

            # Extract usage statistics
            usage = response.usage
            prompt_tokens = usage.input_tokens if hasattr(usage, "input_tokens") else 0
            completion_tokens = usage.output_tokens if hasattr(usage, "output_tokens") else 0

            # Extract finish reason
            finish_reason = response.stop_reason if hasattr(response, "stop_reason") else "unknown"

            return {
                "output_text": output_text,
                "finish_reason": finish_reason,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
                "model": response.model if hasattr(response, "model") else model,
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
