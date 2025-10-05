"""Verify experiment constants alignment between docs and config.py."""

import sys
from pathlib import Path

# Import constants from config
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import PRODUCTS, MATERIALS, TIMES, TEMPS, REPS, ENGINES, REGION


def verify_constants():
    """Verify all constants match expected values from docs."""
    errors = []

    # Expected values from docs/experiment_constants.md
    # Current: 3 products (future: 5)
    expected_products = (
        "smartphone",
        "cryptocurrency",
        "supplement_melatonin",
    )

    expected_materials = (
        "digital_ad.j2",
        "organic_social_posts.j2",
        "faq.j2",
        "spec_document_facts_only.j2",
        "blog_post_promo.j2",
    )

    expected_times = ("morning", "afternoon", "evening")

    expected_temps = (0.2, 0.6, 1.0)

    expected_reps = (1, 2, 3)

    expected_engines = ("openai", "google", "mistral")

    expected_region = "US"

    # Verify each constant
    if PRODUCTS != expected_products:
        errors.append(f"PRODUCTS mismatch: {PRODUCTS} != {expected_products}")

    if MATERIALS != expected_materials:
        errors.append(f"MATERIALS mismatch: {MATERIALS} != {expected_materials}")

    if TIMES != expected_times:
        errors.append(f"TIMES mismatch: {TIMES} != {expected_times}")

    if TEMPS != expected_temps:
        errors.append(f"TEMPS mismatch: {TEMPS} != {expected_temps}")

    if REPS != expected_reps:
        errors.append(f"REPS mismatch: {REPS} != {expected_reps}")

    if ENGINES != expected_engines:
        errors.append(f"ENGINES mismatch: {ENGINES} != {expected_engines}")

    if REGION != expected_region:
        errors.append(f"REGION mismatch: {REGION} != {expected_region}")

    # Calculate matrix size
    matrix_size = (
        len(PRODUCTS)
        * len(MATERIALS)
        * len(TIMES)
        * len(TEMPS)
        * len(REPS)
        * len(ENGINES)
    )

    expected_matrix_size = 1215  # 3 products × 5 × 3 × 3 × 3 × 3
    if matrix_size != expected_matrix_size:
        errors.append(
            f"Matrix size mismatch: {matrix_size} != {expected_matrix_size} "
            f"({len(PRODUCTS)} × {len(MATERIALS)} × {len(TIMES)} × "
            f"{len(TEMPS)} × {len(REPS)} × {len(ENGINES)})"
        )

    # Report results
    if errors:
        print("✗ Constants verification FAILED:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
    else:
        print("✓ All constants verified")
        print(f"  Matrix size: {matrix_size} runs")
        print(f"  Products: {len(PRODUCTS)}")
        print(f"  Materials: {len(MATERIALS)}")
        print(f"  Times: {len(TIMES)}")
        print(f"  Temperatures: {len(TEMPS)}")
        print(f"  Repetitions: {len(REPS)}")
        print(f"  Engines: {len(ENGINES)}")
        print(f"  Region: {REGION}")


if __name__ == "__main__":
    verify_constants()
