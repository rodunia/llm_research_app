#!/usr/bin/env python
"""Comprehensive test script for automatic materials generation.

Tests:
A. Trap flag behavior (trap_flag=True vs False)
B. All 5 material types
C. Multiple engines (OpenAI, Google, Mistral)
D. Mini batch (1 product × 5 materials × available engines)

Usage:
    python test_comprehensive.py
"""

import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from runner.render import load_product_yaml, render_prompt
from runner.engines.openai_client import call_openai
from runner.engines.google_client import call_google
from runner.engines.mistral_client import call_mistral

# Load environment
load_dotenv()

# Configuration
PRODUCT_ID = "smartphone_mid"
MATERIALS = [
    "digital_ad.j2",
    "organic_social_posts.j2",
    "faq.j2",
    "spec_document_facts_only.j2",
    "blog_post_promo.j2"
]
TEMPERATURE = 0.7

# Results directory
RESULTS_DIR = Path("outputs/comprehensive_test")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

def call_engine(engine: str, prompt: str, temperature: float):
    """Route to appropriate engine."""
    if engine == "openai":
        return call_openai(prompt=prompt, temperature=temperature)
    elif engine == "google":
        return call_google(prompt=prompt, temperature=temperature)
    elif engine == "mistral":
        return call_mistral(prompt=prompt, temperature=temperature)
    else:
        raise ValueError(f"Unknown engine: {engine}")

def get_available_engines():
    """Detect which engines have API keys."""
    engines = []
    if os.getenv("OPENAI_API_KEY"):
        engines.append("openai")
    if os.getenv("GOOGLE_API_KEY"):
        engines.append("google")
    if os.getenv("MISTRAL_API_KEY"):
        engines.append("mistral")
    return engines

def save_result(test_name: str, content: str, subdir: str = ""):
    """Save test result to file."""
    if subdir:
        output_dir = RESULTS_DIR / subdir
        output_dir.mkdir(parents=True, exist_ok=True)
    else:
        output_dir = RESULTS_DIR

    filepath = output_dir / f"{test_name}.txt"
    filepath.write_text(content, encoding="utf-8")
    return filepath

def test_a_trap_flag():
    """Test A: Trap flag behavior (True vs False)."""
    print("\n" + "="*70)
    print("TEST A: Trap Flag Behavior")
    print("="*70 + "\n")

    product_path = Path("products") / f"{PRODUCT_ID}.yaml"
    product_yaml = load_product_yaml(product_path)
    material = "digital_ad.j2"

    results = []

    for trap_flag in [False, True]:
        trap_label = "WITH_TRAP" if trap_flag else "NO_TRAP"
        print(f"\nTesting {trap_label}...")

        # Render prompt
        prompt_text = render_prompt(
            product_yaml=product_yaml,
            template_name=material,
            trap_flag=trap_flag
        )

        # Call OpenAI (or first available)
        engines = get_available_engines()
        if not engines:
            print("❌ No API keys available")
            return []

        engine = engines[0]
        response = call_engine(engine, prompt_text, TEMPERATURE)

        # Save prompt and output
        save_result(f"prompt_{trap_label}", prompt_text, "test_a_trap")
        save_result(f"output_{trap_label}", response["output_text"], "test_a_trap")

        result = {
            "trap_flag": trap_flag,
            "trap_label": trap_label,
            "engine": engine,
            "model": response.get("model", "N/A"),
            "output": response["output_text"],
            "tokens": response.get("total_tokens", 0)
        }
        results.append(result)

        print(f"✓ {trap_label}: {len(response['output_text'])} chars, {response.get('total_tokens', 0)} tokens")

    # Save comparison
    comparison = f"""Trap Flag Comparison Test
========================

Product: {product_yaml['name']}
Material: {material}
Engine: {results[0]['engine']}

NO TRAP OUTPUT:
{'-'*70}
{results[0]['output']}

WITH TRAP OUTPUT:
{'-'*70}
{results[1]['output']}

ANALYSIS:
- No trap tokens: {results[0]['tokens']}
- With trap tokens: {results[1]['tokens']}
- Difference: {results[1]['tokens'] - results[0]['tokens']} tokens
"""
    save_result("comparison", comparison, "test_a_trap")

    print(f"\n✓ Test A complete. Results saved to {RESULTS_DIR}/test_a_trap/")
    return results

def test_b_all_materials():
    """Test B: All 5 material types."""
    print("\n" + "="*70)
    print("TEST B: All 5 Material Types")
    print("="*70 + "\n")

    product_path = Path("products") / f"{PRODUCT_ID}.yaml"
    product_yaml = load_product_yaml(product_path)

    engines = get_available_engines()
    if not engines:
        print("❌ No API keys available")
        return []

    engine = engines[0]
    print(f"Using engine: {engine}\n")

    results = []

    for i, material in enumerate(MATERIALS, 1):
        print(f"[{i}/{len(MATERIALS)}] Testing {material}...")

        # Render prompt
        prompt_text = render_prompt(
            product_yaml=product_yaml,
            template_name=material,
            trap_flag=False
        )

        # Call engine
        response = call_engine(engine, prompt_text, TEMPERATURE)

        # Save files
        material_name = material.replace(".j2", "")
        save_result(f"{material_name}_prompt", prompt_text, "test_b_materials")
        save_result(f"{material_name}_output", response["output_text"], "test_b_materials")

        result = {
            "material": material,
            "engine": engine,
            "model": response.get("model", "N/A"),
            "output": response["output_text"],
            "tokens": response.get("total_tokens", 0),
            "prompt_len": len(prompt_text),
            "output_len": len(response["output_text"])
        }
        results.append(result)

        print(f"  ✓ Output: {result['output_len']} chars, {result['tokens']} tokens")

    # Save summary
    summary = f"""All Materials Test Summary
========================

Product: {product_yaml['name']}
Engine: {engine}
Materials tested: {len(MATERIALS)}

"""
    for r in results:
        summary += f"\n{r['material']}:\n"
        summary += f"  Prompt: {r['prompt_len']} chars\n"
        summary += f"  Output: {r['output_len']} chars\n"
        summary += f"  Tokens: {r['tokens']}\n"
        summary += f"  Model: {r['model']}\n"

    save_result("summary", summary, "test_b_materials")

    print(f"\n✓ Test B complete. Results saved to {RESULTS_DIR}/test_b_materials/")
    return results

def test_c_multiple_engines():
    """Test C: Multiple engines comparison."""
    print("\n" + "="*70)
    print("TEST C: Multiple Engines Comparison")
    print("="*70 + "\n")

    engines = get_available_engines()
    if not engines:
        print("❌ No API keys available")
        return []

    print(f"Available engines: {', '.join(engines)}\n")

    product_path = Path("products") / f"{PRODUCT_ID}.yaml"
    product_yaml = load_product_yaml(product_path)
    material = "digital_ad.j2"

    # Render prompt once
    prompt_text = render_prompt(
        product_yaml=product_yaml,
        template_name=material,
        trap_flag=False
    )

    save_result("shared_prompt", prompt_text, "test_c_engines")

    results = []

    for i, engine in enumerate(engines, 1):
        print(f"[{i}/{len(engines)}] Testing {engine}...")

        try:
            response = call_engine(engine, prompt_text, TEMPERATURE)

            # Save output
            save_result(f"{engine}_output", response["output_text"], "test_c_engines")

            result = {
                "engine": engine,
                "model": response.get("model", "N/A"),
                "output": response["output_text"],
                "tokens": response.get("total_tokens", 0),
                "prompt_tokens": response.get("prompt_tokens", 0),
                "completion_tokens": response.get("completion_tokens", 0)
            }
            results.append(result)

            print(f"  ✓ Model: {result['model']}")
            print(f"  ✓ Tokens: {result['tokens']}")

        except Exception as e:
            print(f"  ❌ Failed: {e}")

    # Save comparison
    comparison = f"""Engine Comparison Test
====================

Product: {product_yaml['name']}
Material: {material}
Temperature: {TEMPERATURE}

Prompt (shared across all engines):
{'-'*70}
{prompt_text}

"""
    for r in results:
        comparison += f"\n{'='*70}\n"
        comparison += f"ENGINE: {r['engine'].upper()}\n"
        comparison += f"Model: {r['model']}\n"
        comparison += f"Tokens: {r['prompt_tokens']} prompt + {r['completion_tokens']} completion = {r['tokens']} total\n"
        comparison += f"{'-'*70}\n"
        comparison += f"{r['output']}\n"

    save_result("comparison", comparison, "test_c_engines")

    print(f"\n✓ Test C complete. Results saved to {RESULTS_DIR}/test_c_engines/")
    return results

def test_d_mini_batch():
    """Test D: Mini batch (1 product × 5 materials × available engines)."""
    print("\n" + "="*70)
    print("TEST D: Mini Batch")
    print("="*70 + "\n")

    engines = get_available_engines()
    if not engines:
        print("❌ No API keys available")
        return []

    product_path = Path("products") / f"{PRODUCT_ID}.yaml"
    product_yaml = load_product_yaml(product_path)

    total_runs = len(MATERIALS) * len(engines)
    print(f"Running {total_runs} experiments:")
    print(f"  1 product × {len(MATERIALS)} materials × {len(engines)} engines\n")

    results = []
    run_count = 0

    for material in MATERIALS:
        material_name = material.replace(".j2", "")

        for engine in engines:
            run_count += 1
            print(f"[{run_count}/{total_runs}] {engine} × {material_name}...", end=" ")

            try:
                # Render prompt
                prompt_text = render_prompt(
                    product_yaml=product_yaml,
                    template_name=material,
                    trap_flag=False
                )

                # Call engine
                response = call_engine(engine, prompt_text, TEMPERATURE)

                # Save files
                run_id = f"{engine}_{material_name}"
                save_result(f"{run_id}_prompt", prompt_text, "test_d_batch")
                save_result(f"{run_id}_output", response["output_text"], "test_d_batch")

                result = {
                    "run_id": run_id,
                    "material": material,
                    "engine": engine,
                    "model": response.get("model", "N/A"),
                    "output": response["output_text"],
                    "tokens": response.get("total_tokens", 0),
                    "status": "completed"
                }
                results.append(result)

                print(f"✓ {result['tokens']} tokens")

            except Exception as e:
                print(f"❌ {e}")
                results.append({
                    "run_id": f"{engine}_{material_name}",
                    "material": material,
                    "engine": engine,
                    "status": "failed",
                    "error": str(e)
                })

    # Generate batch summary
    completed = [r for r in results if r.get("status") == "completed"]
    failed = [r for r in results if r.get("status") == "failed"]

    summary = f"""Mini Batch Test Summary
======================

Product: {product_yaml['name']}
Total runs: {total_runs}
Completed: {len(completed)}
Failed: {len(failed)}

Materials: {', '.join(MATERIALS)}
Engines: {', '.join(engines)}

Results by Engine:
"""
    for engine in engines:
        engine_results = [r for r in completed if r["engine"] == engine]
        total_tokens = sum(r["tokens"] for r in engine_results)
        summary += f"\n{engine}:\n"
        summary += f"  Runs: {len(engine_results)}\n"
        summary += f"  Total tokens: {total_tokens}\n"
        summary += f"  Avg tokens/run: {total_tokens/len(engine_results) if engine_results else 0:.0f}\n"

    summary += f"\nResults by Material:\n"
    for material in MATERIALS:
        material_name = material.replace(".j2", "")
        material_results = [r for r in completed if r["material"] == material]
        summary += f"\n{material_name}:\n"
        summary += f"  Runs: {len(material_results)}\n"
        for r in material_results:
            summary += f"    {r['engine']}: {r['tokens']} tokens\n"

    if failed:
        summary += f"\nFailed runs:\n"
        for r in failed:
            summary += f"  {r['run_id']}: {r.get('error', 'Unknown error')}\n"

    save_result("batch_summary", summary, "test_d_batch")

    print(f"\n✓ Test D complete. Results saved to {RESULTS_DIR}/test_d_batch/")
    return results

def main():
    """Run all comprehensive tests."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print("\n" + "="*70)
    print("COMPREHENSIVE MATERIALS GENERATION TEST SUITE")
    print(f"Started: {timestamp}")
    print("="*70)

    engines = get_available_engines()
    if not engines:
        print("\n❌ ERROR: No API keys found!")
        print("Set OPENAI_API_KEY, GOOGLE_API_KEY, or MISTRAL_API_KEY in .env")
        return

    print(f"\nAvailable engines: {', '.join(engines)}")
    print(f"Product: {PRODUCT_ID}")
    print(f"Materials: {len(MATERIALS)}")
    print(f"Output directory: {RESULTS_DIR}")

    # Run all tests
    results_a = test_a_trap_flag()
    results_b = test_b_all_materials()
    results_c = test_c_multiple_engines()
    results_d = test_d_mini_batch()

    # Master summary
    print("\n" + "="*70)
    print("ALL TESTS COMPLETE")
    print("="*70)

    master_summary = f"""Comprehensive Test Suite - Master Summary
========================================

Timestamp: {timestamp}
Product: {PRODUCT_ID}
Available engines: {', '.join(engines)}

Test A - Trap Flag:
  Runs: {len(results_a)}
  Location: {RESULTS_DIR}/test_a_trap/

Test B - All Materials:
  Runs: {len(results_b)}
  Materials: {len(MATERIALS)}
  Location: {RESULTS_DIR}/test_b_materials/

Test C - Multiple Engines:
  Runs: {len(results_c)}
  Engines: {len(engines)}
  Location: {RESULTS_DIR}/test_c_engines/

Test D - Mini Batch:
  Runs: {len(results_d)}
  Total combinations: {len(MATERIALS)} materials × {len(engines)} engines = {len(MATERIALS) * len(engines)}
  Location: {RESULTS_DIR}/test_d_batch/

RESULTS SUMMARY:
- All prompts saved with '_prompt' suffix
- All outputs saved with '_output' suffix
- Comparison/summary files in each test directory
- Master summary: {RESULTS_DIR}/MASTER_SUMMARY.txt
"""

    save_result("MASTER_SUMMARY", master_summary, "")

    print(master_summary)
    print(f"\n📁 All results saved to: {RESULTS_DIR}/")
    print("\nTo view results:")
    print(f"  ls -R {RESULTS_DIR}")
    print(f"  cat {RESULTS_DIR}/MASTER_SUMMARY.txt")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ TEST SUITE FAILED: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
