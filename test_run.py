#!/usr/bin/env python
"""
test_run.py - Simple test script to verify LLM research app is working
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from runner.engines.openai_client import call_openai
from runner.engines.google_client import call_google
from runner.engines.anthropic_client import call_anthropic

# Load environment variables
load_dotenv()

def test_basic_query():
    """Test a simple query across available providers"""

    test_prompt = "Say 'Hello, World!' and nothing else."

    print("Starting test run...\n")

    # Test OpenAI (if key available)
    if os.getenv("OPENAI_API_KEY"):
        print("Testing OpenAI...")
        result = call_openai(
            prompt=test_prompt,
            temperature=0.7,
            max_tokens=50
        )
        print(f"Response: {result['output_text']}")
        print(f"Model: {result['model']}")
        print(f"Tokens: {result['total_tokens']}\n")

    # Test Google (if key available)
    if os.getenv("GOOGLE_API_KEY"):
        print("Testing Google Gemini...")
        result = call_google(
            prompt=test_prompt,
            temperature=0.7,
            max_tokens=50
        )
        print(f"Response: {result['output_text']}")
        print(f"Model: {result['model']}")
        print(f"Tokens: {result['total_tokens']}\n")

    # Test Anthropic (if key available)
    if os.getenv("ANTHROPIC_API_KEY"):
        print("Testing Anthropic Claude...")
        result = call_anthropic(
            prompt=test_prompt,
            temperature=0.7,
            max_tokens=50
        )
        print(f"Response: {result['output_text']}")
        print(f"Model: {result['model']}")
        print(f"Tokens: {result['total_tokens']}\n")

    print("✓ Test run complete! All configured engines working.")

if __name__ == "__main__":
    test_basic_query()
