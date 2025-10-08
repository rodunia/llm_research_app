#!/usr/bin/env python
"""Quick test script to verify automatic materials generation for 1 product and 1 run.

Usage:
    python test_single_run.py

This will:
1. Load smartphone_mid.yaml
2. Render digital_ad.j2 template
3. Send to OpenAI (or Google if OpenAI unavailable)
4. Save output to outputs/test/
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from runner.render import load_product_yaml, render_prompt
from runner.engines.openai_client import call_openai
from runner.engines.google_client import call_google

# Load environment
load_dotenv()

def test_single_material_generation():
    """Test automatic material generation with 1 product and 1 template."""

    print("\n" + "="*60)
    print("TEST: Automatic Materials Generation")
    print("="*60 + "\n")

    # Configuration
    product_id = "smartphone_mid"
    material_type = "digital_ad.j2"
    temperature = 0.7
    trap_flag = False

    print(f"Product: {product_id}")
    print(f"Material: {material_type}")
    print(f"Temperature: {temperature}")
    print(f"Trap: {trap_flag}\n")

    # Step 1: Load product YAML
    print("Step 1: Loading product YAML...")
    product_path = Path("products") / f"{product_id}.yaml"

    if not product_path.exists():
        print(f"❌ Error: Product file not found: {product_path}")
        return False

    product_yaml = load_product_yaml(product_path)
    print(f"✓ Loaded: {product_yaml['name']}")

    # Step 2: Render prompt template
    print("\nStep 2: Rendering prompt template...")
    prompt_text = render_prompt(
        product_yaml=product_yaml,
        template_name=material_type,
        trap_flag=trap_flag
    )
    print(f"✓ Rendered prompt ({len(prompt_text)} chars)")
    print("\n--- RENDERED PROMPT ---")
    print(prompt_text)
    print("--- END PROMPT ---\n")

    # Step 3: Call LLM engine
    print("Step 3: Calling LLM engine...")

    # Try OpenAI first, fallback to Google
    if os.getenv("OPENAI_API_KEY"):
        print("Using OpenAI...")
        response = call_openai(
            prompt=prompt_text,
            temperature=temperature
        )
        engine_used = "openai"
    elif os.getenv("GOOGLE_API_KEY"):
        print("Using Google Gemini...")
        response = call_google(
            prompt=prompt_text,
            temperature=temperature
        )
        engine_used = "google"
    else:
        print("❌ Error: No API keys found. Set OPENAI_API_KEY or GOOGLE_API_KEY in .env")
        return False

    print(f"✓ Response received from {engine_used}")

    # Step 4: Display results
    print("\n" + "="*60)
    print("GENERATED OUTPUT")
    print("="*60 + "\n")
    print(response["output_text"])
    print("\n" + "="*60)

    # Step 5: Show metrics
    print("\nMETRICS:")
    print(f"  Model: {response.get('model', 'N/A')}")
    print(f"  Prompt tokens: {response.get('prompt_tokens', 0)}")
    print(f"  Completion tokens: {response.get('completion_tokens', 0)}")
    print(f"  Total tokens: {response.get('total_tokens', 0)}")
    print(f"  Finish reason: {response.get('finish_reason', 'N/A')}")

    # Step 6: Save to test output directory
    print("\nStep 6: Saving outputs...")
    test_output_dir = Path("outputs/test")
    test_output_dir.mkdir(parents=True, exist_ok=True)

    # Save prompt
    prompt_file = test_output_dir / "test_prompt.txt"
    prompt_file.write_text(prompt_text, encoding="utf-8")
    print(f"✓ Saved prompt: {prompt_file}")

    # Save output
    output_file = test_output_dir / "test_output.txt"
    output_file.write_text(response["output_text"], encoding="utf-8")
    print(f"✓ Saved output: {output_file}")

    # Save metadata
    metadata_file = test_output_dir / "test_metadata.txt"
    metadata = f"""Test Run Metadata
==================
Product: {product_id}
Product Name: {product_yaml['name']}
Material Type: {material_type}
Engine: {engine_used}
Model: {response.get('model', 'N/A')}
Temperature: {temperature}
Trap Flag: {trap_flag}

Metrics:
- Prompt tokens: {response.get('prompt_tokens', 0)}
- Completion tokens: {response.get('completion_tokens', 0)}
- Total tokens: {response.get('total_tokens', 0)}
- Finish reason: {response.get('finish_reason', 'N/A')}
- Output length: {len(response['output_text'])} chars
"""
    metadata_file.write_text(metadata, encoding="utf-8")
    print(f"✓ Saved metadata: {metadata_file}")

    print("\n" + "="*60)
    print("✓ TEST PASSED - Materials generation working correctly!")
    print("="*60 + "\n")

    return True

if __name__ == "__main__":
    try:
        success = test_single_material_generation()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ TEST FAILED with error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
