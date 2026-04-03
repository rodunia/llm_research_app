"""
Mini Live Test - End-to-End Validation

Tests actual LLM API calls with 3 runs (1 per engine) to validate:
- API authentication works for all engines
- Prompts render and execute correctly
- Output files write successfully
- CSV tracking works
- Error handling works
- Runtime and cost estimation

Usage:
    python scripts/test_mini_live_run.py
"""

import sys
import time
import random
from pathlib import Path
from datetime import datetime
import os

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# NOTE: No need to call load_dotenv() here - engine clients do it automatically!

from config import PRODUCTS, MATERIALS, TEMPS, ENGINES
from runner.render import load_product_yaml, render_prompt
from runner.utils import make_run_id
from runner.engines.openai_client import call_openai
from runner.engines.google_client import call_google
from runner.engines.mistral_client import call_mistral

# ==================== CONFIGURATION ====================

OUTPUT_DIR = Path("outputs")
RESULTS_DIR = Path("results")
TEST_LOG_CSV = RESULTS_DIR / "mini_live_test_log.csv"

# Fixed seed for reproducibility
RANDOM_SEED = 99


# ==================== ENGINE MAPPING ====================

ENGINE_FUNCTIONS = {
    'openai': call_openai,
    'google': call_google,
    'mistral': call_mistral
}


# ==================== HELPER FUNCTIONS ====================

def select_test_runs(num_runs: int = 3, seed: int = RANDOM_SEED):
    """
    Select test runs - one per engine.

    Returns:
        List of (product, material, temp, engine) tuples
    """
    random.seed(seed)

    test_runs = []

    # Ensure one run per engine
    for engine in ENGINES:
        product = random.choice(PRODUCTS)
        material = random.choice(MATERIALS)
        temp = random.choice(TEMPS)

        test_runs.append({
            'product_id': product,
            'material_type': material,
            'temperature': temp,
            'engine': engine,
            'repetition': 1  # First rep for testing
        })

    return test_runs


def run_single_test(run_config: dict) -> dict:
    """
    Execute a single test run with real API call.

    Returns:
        Dict with results (success, output, tokens, error, etc.)
    """
    product_id = run_config['product_id']
    material_type = run_config['material_type']
    temperature = run_config['temperature']
    engine = run_config['engine']
    repetition = run_config['repetition']

    print(f"\n{'=' * 70}")
    print(f"TEST RUN: {engine} | {product_id} | {material_type} | temp={temperature}")
    print(f"{'=' * 70}")

    result = {
        'run_config': run_config,
        'success': False,
        'error': None,
        'output_text': None,
        'prompt_tokens': None,
        'completion_tokens': None,
        'total_tokens': None,
        'runtime_seconds': None,
        'run_id': None,
        'output_path': None
    }

    try:
        # STEP 1: Load product YAML
        print("  [1/5] Loading product YAML...")
        product_path = Path(f"products/{product_id}.yaml")
        product_yaml = load_product_yaml(product_path)
        print(f"        ✅ Loaded: {product_path}")

        # STEP 2: Render prompt
        print("  [2/5] Rendering prompt...")
        prompt_text = render_prompt(
            product_yaml=product_yaml,
            template_name=material_type,
            trap_flag=False
        )
        print(f"        ✅ Rendered {len(prompt_text)} chars")

        # STEP 3: Generate run_id
        print("  [3/5] Generating run_id...")
        knobs = {
            'product_id': product_id,
            'material_type': material_type,
            'engine': engine,
            'time_of_day_label': 'test',
            'temperature_label': str(temperature),
            'repetition_id': repetition,
            'trap_flag': False
        }
        run_id = make_run_id(knobs, prompt_text)
        result['run_id'] = run_id
        print(f"        ✅ run_id: {run_id[:16]}...")

        # STEP 4: Call LLM API
        print(f"  [4/5] Calling {engine} API...")
        start_time = time.time()

        engine_func = ENGINE_FUNCTIONS[engine]
        api_response = engine_func(
            prompt=prompt_text,
            temperature=temperature,
            max_tokens=2000,
            seed=12345
        )

        runtime = time.time() - start_time
        result['runtime_seconds'] = runtime

        # Extract response
        output_text = api_response.get('output_text', '')
        result['output_text'] = output_text
        result['prompt_tokens'] = api_response.get('prompt_tokens', 0)
        result['completion_tokens'] = api_response.get('completion_tokens', 0)
        result['total_tokens'] = api_response.get('total_tokens', 0)

        print(f"        ✅ API call succeeded ({runtime:.2f}s)")
        print(f"        📊 Tokens: {result['prompt_tokens']} prompt + {result['completion_tokens']} completion = {result['total_tokens']} total")
        print(f"        📝 Output length: {len(output_text)} chars")

        # STEP 5: Write output file
        print("  [5/5] Writing output file...")
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = OUTPUT_DIR / f"{run_id}.txt"

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(output_text)

        result['output_path'] = str(output_path)
        print(f"        ✅ Saved to: {output_path}")

        # Mark as success
        result['success'] = True
        print(f"\n✅ TEST RUN SUCCEEDED")

    except Exception as e:
        result['error'] = str(e)
        print(f"\n❌ TEST RUN FAILED: {e}")

    return result


def save_test_log(results: list):
    """Save test results to CSV log."""
    import csv

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        'engine', 'product_id', 'material_type', 'temperature', 'repetition',
        'success', 'error', 'run_id', 'output_path',
        'prompt_tokens', 'completion_tokens', 'total_tokens',
        'runtime_seconds', 'output_length_chars'
    ]

    with open(TEST_LOG_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for result in results:
            row = {
                'engine': result['run_config']['engine'],
                'product_id': result['run_config']['product_id'],
                'material_type': result['run_config']['material_type'],
                'temperature': result['run_config']['temperature'],
                'repetition': result['run_config']['repetition'],
                'success': result['success'],
                'error': result['error'],
                'run_id': result['run_id'],
                'output_path': result['output_path'],
                'prompt_tokens': result['prompt_tokens'],
                'completion_tokens': result['completion_tokens'],
                'total_tokens': result['total_tokens'],
                'runtime_seconds': result['runtime_seconds'],
                'output_length_chars': len(result['output_text']) if result['output_text'] else 0
            }
            writer.writerow(row)

    print(f"\n📊 Test log saved to: {TEST_LOG_CSV}")


def print_summary(results: list):
    """Print summary statistics."""
    print("\n" + "=" * 70)
    print("MINI LIVE TEST SUMMARY")
    print("=" * 70)

    total = len(results)
    successful = sum(1 for r in results if r['success'])
    failed = total - successful

    print(f"\nTotal runs: {total}")
    print(f"  ✅ Successful: {successful}")
    print(f"  ❌ Failed: {failed}")

    if successful > 0:
        print(f"\nPerformance Metrics:")

        # Runtime stats
        runtimes = [r['runtime_seconds'] for r in results if r['success']]
        avg_runtime = sum(runtimes) / len(runtimes)
        print(f"  Average runtime: {avg_runtime:.2f}s per run")

        # Token stats
        total_tokens = sum(r['total_tokens'] for r in results if r['success'])
        avg_tokens = total_tokens / successful
        print(f"  Average tokens: {avg_tokens:.0f} per run")

        # Cost estimation (rough)
        # Assuming ~$0.01 per 1K tokens average across models
        estimated_cost_per_run = (avg_tokens / 1000) * 0.01
        estimated_total_cost = estimated_cost_per_run * 1620

        print(f"\nCost Estimation:")
        print(f"  Estimated cost per run: ${estimated_cost_per_run:.4f}")
        print(f"  Estimated total for 1,620 runs: ${estimated_total_cost:.2f}")

        # Time estimation
        total_runtime_hours = (avg_runtime * 1620) / 3600
        print(f"\nTime Estimation:")
        print(f"  Estimated total runtime: {total_runtime_hours:.1f} hours ({total_runtime_hours/24:.1f} days)")

    if failed > 0:
        print(f"\n❌ Failures:")
        for r in results:
            if not r['success']:
                print(f"  - {r['run_config']['engine']}: {r['error']}")

    print("\n" + "=" * 70)

    if successful == total:
        print("✅ ALL TESTS PASSED - Ready for full experiment!")
    else:
        print("⚠️  SOME TESTS FAILED - Fix issues before full experiment")

    print("=" * 70)


# ==================== MAIN ====================

def main():
    """Run mini live test."""
    print("=" * 70)
    print("MINI LIVE TEST - END-TO-END VALIDATION")
    print("=" * 70)
    print("\nThis will make REAL API calls to test all engines.")
    print("Estimated cost: ~$0.05-0.15")
    print("")

    # Confirm
    response = input("Proceed with live test? (y/n): ")
    if response.lower() != 'y':
        print("Test cancelled.")
        return

    print("\n" + "=" * 70)
    print("SELECTING TEST RUNS")
    print("=" * 70)

    # Select test runs (one per engine)
    test_runs = select_test_runs(num_runs=3, seed=RANDOM_SEED)

    print(f"\nSelected {len(test_runs)} test runs:")
    for i, run in enumerate(test_runs, 1):
        print(f"  {i}. {run['engine']:8s} | {run['product_id']:25s} | {run['material_type']:20s} | temp={run['temperature']}")

    # Execute test runs
    print("\n" + "=" * 70)
    print("EXECUTING TEST RUNS")
    print("=" * 70)

    results = []
    for run_config in test_runs:
        result = run_single_test(run_config)
        results.append(result)
        time.sleep(1)  # Brief pause between runs

    # Save log
    save_test_log(results)

    # Print summary
    print_summary(results)


if __name__ == "__main__":
    main()
