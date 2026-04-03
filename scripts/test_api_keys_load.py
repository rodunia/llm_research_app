"""
Test that API keys load correctly without explicit load_dotenv() call.

This script does NOT call load_dotenv() - it relies on engine clients
to load .env automatically.
"""

# DON'T import dotenv or call load_dotenv() here - testing that engines do it
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import engines directly (they should load .env automatically)
from runner.engines.openai_client import call_openai
from runner.engines.google_client import call_google
from runner.engines.mistral_client import call_mistral

def test_api_keys():
    """Test that all engines can access API keys."""

    print("=" * 70)
    print("TESTING API KEY LOADING")
    print("=" * 70)
    print("\nThis script does NOT call load_dotenv() explicitly.")
    print("Engine clients should load .env automatically.\n")

    # Test 1: Try to call each engine with minimal request
    test_prompt = "Say 'API key works' and nothing else."

    engines_to_test = [
        ('openai', call_openai),
        ('google', call_google),
        ('mistral', call_mistral)
    ]

    results = []

    for engine_name, engine_func in engines_to_test:
        print(f"Testing {engine_name}...")
        try:
            # Just test API call succeeds (validates API key works)
            response = engine_func(
                prompt=test_prompt,
                temperature=0.0,
                max_tokens=10
            )

            print(f"  ✅ {engine_name}: API key loaded successfully")
            results.append((engine_name, True, None))

        except ValueError as e:
            # This is the error we get when API key is missing
            if "API_KEY" in str(e):
                print(f"  ❌ {engine_name}: {e}")
                results.append((engine_name, False, str(e)))
            else:
                raise

        except Exception as e:
            # Other errors (network, etc.) are OK - we just need to know key loaded
            print(f"  ⚠️  {engine_name}: API key loaded, but got error: {e}")
            results.append((engine_name, True, f"Non-key error: {e}"))

    # Summary
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)

    successes = sum(1 for _, success, _ in results if success)
    failures = len(results) - successes

    print(f"\nAPI keys loaded: {successes}/{len(results)}")

    if failures > 0:
        print("\n❌ FAILED ENGINES:")
        for name, success, error in results:
            if not success:
                print(f"  - {name}: {error}")
    else:
        print("\n✅ ALL API KEYS LOADED SUCCESSFULLY")
        print("Engine clients now self-contain .env loading!")

    print("=" * 70)

if __name__ == "__main__":
    test_api_keys()
