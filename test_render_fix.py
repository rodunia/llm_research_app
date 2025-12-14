#!/usr/bin/env python3
"""Test that render.py works with enhanced YAMLs."""

from pathlib import Path
from runner.render import load_product_yaml, render_prompt

def test_product(product_id: str):
    """Test rendering a product."""
    print(f"\n{'='*60}")
    print(f"Testing: {product_id}")
    print(f"{'='*60}")

    # Load product YAML
    yaml_path = Path(f"products/{product_id}.yaml")
    product_data = load_product_yaml(yaml_path)

    print(f"✓ Loaded YAML: {product_data['name']}")
    print(f"  Keys present: {sorted(product_data.keys())}")

    # Try rendering a template
    template = "digital_ad.j2"
    try:
        rendered = render_prompt(product_data, template, trap_flag=False)
        print(f"✓ Rendered template: {template}")
        print(f"  Prompt length: {len(rendered)} characters")
        print(f"\n  First 200 chars:\n  {rendered[:200]}...")
        return True
    except Exception as e:
        print(f"✗ Failed to render: {e}")
        return False

if __name__ == "__main__":
    products = [
        "supplement_melatonin",
        "cryptocurrency_corecoin",
        "smartphone_mid"
    ]

    results = {}
    for product_id in products:
        try:
            results[product_id] = test_product(product_id)
        except Exception as e:
            print(f"✗ ERROR testing {product_id}: {e}")
            results[product_id] = False

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    for product_id, success in results.items():
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {product_id}")

    all_passed = all(results.values())
    if all_passed:
        print("\n🎉 All tests passed! render.py works with enhanced YAMLs.")
    else:
        print("\n❌ Some tests failed.")
        exit(1)
