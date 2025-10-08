"""Google Gemini API client with retry and timeout handling."""

import os
import time
from typing import Dict, Any, Optional

import google.generativeai as genai
from google.api_core import exceptions

from config import ENGINE_MODELS


def call_google(
    prompt: str,
    temperature: float,
    model: Optional[str] = None,
    max_tokens: int = 2048,
    timeout: int = 60,
    max_retries: int = 3,
) -> Dict[str, Any]:
    """Call Google Gemini API with retry logic.

    Args:
        prompt: User prompt text
        temperature: Sampling temperature (0.0-2.0)
        model: Model identifier (default: from ENGINE_MODELS config)
        max_tokens: Maximum output tokens
        timeout: Request timeout in seconds
        max_retries: Maximum retry attempts

    Returns:
        Dictionary with keys:
            - output_text: Generated text
            - finish_reason: Completion reason
            - prompt_tokens: Input token count (approximate)
            - completion_tokens: Output token count (approximate)
            - total_tokens: Total token count
            - model: Model used

    Raises:
        Exception: If all retries fail
    """
    # Use config default if model not specified
    if model is None:
        model = ENGINE_MODELS["google"]

    # Validate API key
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError(
            "GOOGLE_API_KEY environment variable not set. "
            "Add it to your .env file or set it in your environment."
        )

    genai.configure(api_key=api_key)

    generation_config = {
        "temperature": temperature,
        "max_output_tokens": max_tokens,
    }

    gemini_model = genai.GenerativeModel(
        model_name=model, generation_config=generation_config
    )

    for attempt in range(max_retries):
        try:
            response = gemini_model.generate_content(
                prompt, request_options={"timeout": timeout}
            )

            # Extract text
            output_text = response.text if response.text else ""

            # Manual token counting (Google doesn't provide usage in response)
            prompt_tokens = gemini_model.count_tokens(prompt).total_tokens
            completion_tokens = gemini_model.count_tokens(output_text).total_tokens

            # Get finish reason
            finish_reason = (
                response.candidates[0].finish_reason.name
                if response.candidates
                else "UNKNOWN"
            )

            return {
                "output_text": output_text,
                "finish_reason": finish_reason,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
                "model": model,
            }

        except exceptions.ResourceExhausted as e:
            # Rate limit
            if attempt < max_retries - 1:
                wait_time = 2**attempt
                time.sleep(wait_time)
                continue
            raise

        except exceptions.DeadlineExceeded as e:
            # Timeout
            if attempt < max_retries - 1:
                continue
            raise

        except Exception as e:
            # Non-retryable errors
            raise

    raise Exception("Max retries exceeded")
