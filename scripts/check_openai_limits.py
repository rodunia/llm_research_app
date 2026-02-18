"""Check OpenAI API key tier and rate limits."""

import os
from dotenv import load_dotenv
from openai import OpenAI
import time

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

print("Testing OpenAI API connection and limits...\n")

try:
    # Test with a simple request
    start = time.time()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Say 'test' once"}],
        max_tokens=5
    )
    elapsed = time.time() - start

    print("✅ API Key Valid")
    print(f"✅ Request successful ({elapsed:.2f}s)")
    print(f"Model: {response.model}")
    print(f"Response: {response.choices[0].message.content}")

    # Check response headers for rate limit info
    print("\n📊 Account Information:")
    print("Note: Rate limit details are in HTTP headers, not accessible via SDK")
    print("Attempting to check account tier via models list...")

    # List available models (works for all tiers)
    models = client.models.list()
    model_ids = [m.id for m in models.data]

    has_gpt4 = any('gpt-4' in m for m in model_ids)
    has_o1 = any('o1' in m for m in model_ids)

    print(f"\nAvailable models count: {len(model_ids)}")
    print(f"Has GPT-4 access: {has_gpt4}")
    print(f"Has O1 access: {has_o1}")

    print("\n⚠️  Rate Limit Tiers (OpenAI):")
    print("Free Tier: 3 RPM, 200 RPD")
    print("Tier 1: 500 RPM, 10K tokens/min")
    print("Tier 2: 5,000 RPM, 450K tokens/min")
    print("Tier 3+: 10,000+ RPM")

    print("\n💡 Current issue: 429 errors on ALL requests")
    print("This suggests either:")
    print("1. Free tier (3 RPM) - insufficient for batch processing")
    print("2. Tier 1 with recent heavy usage")
    print("3. Organization-level rate limit restrictions")

except Exception as e:
    print(f"❌ Error: {e}")
    print(f"Error type: {type(e).__name__}")

    if "rate_limit" in str(e).lower() or "429" in str(e):
        print("\n⚠️  RATE LIMIT ERROR")
        print("Your account has hit rate limits before even starting.")
        print("\nRecommended actions:")
        print("1. Check OpenAI usage dashboard: https://platform.openai.com/usage")
        print("2. Check account tier: https://platform.openai.com/settings/organization/limits")
        print("3. Add credits or upgrade tier if on free plan")
        print("4. Wait for limits to reset (1 minute for RPM, 1 day for RPD)")
