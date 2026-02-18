#!/usr/bin/env python3
"""Generate FAQ marketing materials for all products using current prompts."""

import sys
import yaml
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from runner.render import render_prompt, load_product_yaml


def main():
    """Generate FAQ materials for all products."""

    products = [
        'smartphone_mid',
        'cryptocurrency_corecoin',
        'supplement_melatonin'
    ]

    material_type = 'faq.j2'
    trap_flag = False  # Use current standard prompt without trap

    output_dir = Path('docs/faq_samples')
    output_dir.mkdir(exist_ok=True)

    print("=" * 80)
    print("Generating FAQ Marketing Materials")
    print("=" * 80)

    for product_id in products:
        print(f"\n[{product_id}]")

        try:
            # Load product YAML
            product_path = Path('products') / f"{product_id}.yaml"
            product_yaml = load_product_yaml(product_path)

            # Render the prompt using the current template
            rendered_prompt = render_prompt(product_yaml, material_type, trap_flag)

            # Save to file
            output_file = output_dir / f"{product_id}_faq.txt"
            with open(output_file, 'w') as f:
                f.write("=" * 80 + "\n")
                f.write(f"FAQ Marketing Material - {product_id}\n")
                f.write("=" * 80 + "\n\n")
                f.write(rendered_prompt)

            print(f"  ✓ Generated: {output_file}")
            print(f"  Length: {len(rendered_prompt)} characters")

        except Exception as e:
            print(f"  ✗ Error: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 80)
    print(f"All FAQ materials saved to: {output_dir}/")
    print("=" * 80)


if __name__ == '__main__':
    main()
