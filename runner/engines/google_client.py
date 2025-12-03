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

    # Set safety settings to be more permissive for marketing content
    safety_settings = {
        "HARM_CATEGORY_HARASSMENT": "BLOCK_NONE",
        "HARM_CATEGORY_HATE_SPEECH": "BLOCK_NONE",
        "HARM_CATEGORY_SEXUALLY_EXPLICIT": "BLOCK_NONE",
        "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_NONE",
    }

    gemini_model = genai.GenerativeModel(
        model_name=model,
        generation_config=generation_config,
        safety_settings=safety_settings
    )

    for attempt in range(max_retries):
        try:
            response = gemini_model.generate_content(
                prompt, request_options={"timeout": timeout}
            )

            # Check response structure
            finish_reason = "UNKNOWN"
            finish_reason_int = None
            safety_info = []

            if response.candidates:
                candidate = response.candidates[0]

                # Get finish reason (both int and name)
                if hasattr(candidate, 'finish_reason'):
                    finish_reason_int = int(candidate.finish_reason)
                    finish_reason = candidate.finish_reason.name

                # Check safety ratings
                if hasattr(candidate, 'safety_ratings'):
                    for rating in candidate.safety_ratings:
                        if hasattr(rating, 'category') and hasattr(rating, 'probability'):
                            safety_info.append(f"{rating.category.name}: {rating.probability.name}")

            # Extract text safely
            output_text = ""
            try:
                # Check if we have valid parts before accessing text
                if (response.candidates and
                    response.candidates[0].content and
                    response.candidates[0].content.parts):
                    output_text = response.text
            except (ValueError, AttributeError) as e:
                pass  # Expected for blocked content

            # If no output text, determine why
            if not output_text:
                # Finish reason 2 = SAFETY block, 3 = RECITATION, 4 = OTHER
                if finish_reason_int in [2, 3, 4] or finish_reason in ['SAFETY', 'RECITATION', 'OTHER']:
                    if safety_info:
                        safety_details = "\n".join([f"  - {s}" for s in safety_info])
                        output_text = f"""[BLOCKED BY GOOGLE SAFETY FILTERS]

Finish Reason: {finish_reason}

Safety Ratings:
{safety_details}

Google Gemini blocked this content. This is common for:
- Cryptocurrency promotions
- Health/supplement claims
- Financial investment content

Recommendations:
1. Use OpenAI or Mistral (they're more permissive)
2. Try the smartphone product instead
3. Use FAQ template (less promotional)"""
                    else:
                        output_text = f"[BLOCKED: {finish_reason}]\n\nGoogle blocked this content. Try OpenAI or Mistral instead."
                else:
                    output_text = f"[No output - finish_reason: {finish_reason}]"

            # Manual token counting (Google doesn't provide usage in response)
            prompt_tokens = gemini_model.count_tokens(prompt).total_tokens
            completion_tokens = 0
            if output_text and not output_text.startswith("[Content blocked"):
                try:
                    completion_tokens = gemini_model.count_tokens(output_text).total_tokens
                except:
                    completion_tokens = 0

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
