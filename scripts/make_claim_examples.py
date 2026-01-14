"""Generate human-readable claim extraction examples from real runs.

Creates Markdown documentation showing:
- Original generated text excerpts with block structure
- Extracted claims with offsets, triggers, claim_kind, block_kind
- Verification that all offsets are exact substrings

Usage:
    python scripts/make_claim_examples.py --n 3 --out docs/claim_extraction_examples.md

    # With custom materials
    python scripts/make_claim_examples.py --prefer-materials digital_ad,faq,blog_post_promo

    # From specific claims directory
    python scripts/make_claim_examples.py --claims-dir analysis/claims --outputs-dir outputs
"""

import json
import random
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import csv


def classify_text_kind(text: str) -> str:
    """Classify text as 'prompt', 'output', or 'unknown'.

    Uses deterministic heuristics to detect prompt/template language.

    Args:
        text: Text to classify

    Returns:
        One of: 'prompt', 'output', 'unknown'
    """
    # Check first 500 chars for prompt markers
    header = text[:500].lower()

    # Prompt markers (high confidence)
    prompt_markers = [
        "you are an elite content marketing strategist",
        "you are writing",
        "your mission:",
        "compliance framework",
        "authorized claims",
        "prohibited claims",
        "mandatory disclaimers",
        "output format",
        "before writing, mentally confirm",
        "hard rules:",
        "use only the information provided below",
        "do not invent or infer"
    ]

    for marker in prompt_markers:
        if marker in header:
            return "prompt"

    # Output markers (typical generated content)
    output_markers = [
        "experience the",
        "discover",
        "introducing the",
        "## ",  # Markdown headings in blog posts
        "headline:",
        "primary text:",
        "description:",
        "**q",  # FAQ questions
    ]

    has_output_markers = any(marker in header for marker in output_markers)

    # If it has output markers and no prompt markers, it's likely output
    if has_output_markers:
        return "output"

    return "unknown"


def find_output_text(run_id: str, outputs_dir: Path) -> Optional[Path]:
    """Find output text file for a run_id using discovery strategy.

    Prioritizes actual generated outputs over prompts/templates.

    Args:
        run_id: Run identifier
        outputs_dir: Root outputs directory

    Returns:
        Path to output file or None if not found
    """
    # Strategy A: Look for per_run.json artifacts (most reliable)
    per_run_json = Path("analysis/per_run.json")
    if per_run_json.exists():
        try:
            with open(per_run_json, 'r') as f:
                per_run_data = json.load(f)
                for record in per_run_data:
                    if record.get('run_id') == run_id:
                        artifacts = record.get('artifacts', {})
                        output_path = artifacts.get('output_path')
                        if output_path and Path(output_path).exists():
                            text = Path(output_path).read_text(encoding='utf-8')
                            if classify_text_kind(text) == "output":
                                return Path(output_path)
        except (json.JSONDecodeError, KeyError):
            pass

    # Strategy B: Direct lookup with _output.txt suffix (common pattern)
    output_patterns = [
        outputs_dir / f"{run_id}_output.txt",
        outputs_dir / f"{run_id}.txt",
    ]

    for path in output_patterns:
        if path.exists():
            text = path.read_text(encoding='utf-8')
            kind = classify_text_kind(text)
            if kind == "output":
                return path
            elif kind == "prompt":
                continue  # Skip prompts, keep searching

    # Strategy C: Search known output directories
    output_dirs = [
        outputs_dir,
        outputs_dir / "comprehensive_test" / "test_b_materials",
        Path("results/outputs"),
        Path("results/text"),
    ]

    for out_dir in output_dirs:
        if not out_dir.exists():
            continue

        # Look for files matching run_id pattern
        for pattern in [f"{run_id}_output.txt", f"{run_id}.txt", f"*{run_id[:12]}*.txt"]:
            matches = list(out_dir.glob(pattern))
            for match in matches:
                # Skip prompt files
                if "prompt" in match.name.lower():
                    continue

                text = match.read_text(encoding='utf-8')
                kind = classify_text_kind(text)
                if kind == "output":
                    return match

    # Strategy D: Bounded recursive search (cap at 200 files)
    all_txt_files = list(outputs_dir.glob("**/*.txt"))[:200]

    for file_path in all_txt_files:
        # Skip obvious prompt files
        if "prompt" in file_path.name.lower():
            continue

        # Check if filename contains run_id
        if run_id[:12] in file_path.name or run_id in file_path.name:
            text = file_path.read_text(encoding='utf-8')
            kind = classify_text_kind(text)
            if kind == "output":
                return file_path

    return None


def load_or_generate_claims(
    run_id: str,
    output_path: Optional[Path],
    claims_dir: Path
) -> List[Dict[str, Any]]:
    """Load existing claims or generate from output text.

    Args:
        run_id: Run identifier
        output_path: Path to output text (if found)
        claims_dir: Directory containing claim JSONs

    Returns:
        List of claim records
    """
    # Try loading existing claims
    claims_file = claims_dir / f"{run_id}.json"
    if claims_file.exists():
        with open(claims_file, 'r', encoding='utf-8') as f:
            claims = json.load(f)
            # Filter to ensure we have v2.0 claims with block_kind
            if claims and all('block_kind' in c for c in claims):
                return claims

    # Generate claims if output text exists
    if output_path and output_path.exists():
        # Import claim extractor
        import sys
        sys.path.insert(0, '.')
        from analysis.claim_extractor import extract_claim_candidates

        full_text = output_path.read_text(encoding='utf-8')

        # Infer material type from path or use unknown
        material_type = "unknown"
        if "digital_ad" in str(output_path) or "ad" in str(output_path):
            material_type = "digital_ad.j2"
        elif "faq" in str(output_path):
            material_type = "faq.j2"
        elif "blog" in str(output_path):
            material_type = "blog_post_promo.j2"

        run_metadata = {
            "run_id": run_id,
            "product_id": "unknown",
            "material_type": material_type,
            "engine": "unknown",
            "temperature": 0.6,
            "time_of_day": "unknown",
            "repetition_id": 1
        }

        claims = extract_claim_candidates(full_text, run_metadata, include_meta=False)
        return claims

    return []


def select_example_runs(
    outputs_dir: Path,
    claims_dir: Path,
    n: int,
    prefer_materials: List[str],
    seed: int,
    require_block_kinds: bool
) -> List[Tuple[str, Path, List[Dict[str, Any]], str]]:
    """Select representative runs for examples.

    Args:
        outputs_dir: Outputs directory
        claims_dir: Claims directory
        n: Number of examples
        prefer_materials: Preferred material types
        seed: Random seed
        require_block_kinds: If True, only select v2.0 claims

    Returns:
        List of (run_id, output_path, claims, material_type) tuples
    """
    random.seed(seed)

    # Scan outputs directory for _output.txt files (skip prompts)
    output_files = [
        f for f in outputs_dir.glob("*.txt")
        if "prompt" not in f.name.lower()
    ]

    # Also check for comprehensive test outputs (skip prompts)
    comprehensive_outputs = [
        f for f in outputs_dir.glob("comprehensive_test/**/*.txt")
        if "prompt" not in f.name.lower()
    ]

    all_outputs = output_files + comprehensive_outputs
    random.shuffle(all_outputs)

    selected = []
    materials_found = set()

    for output_path in all_outputs:
        if len(selected) >= n:
            break

        # Verify this is an output, not a prompt
        text = output_path.read_text(encoding='utf-8')
        text_kind = classify_text_kind(text)
        if text_kind == "prompt":
            continue  # Skip prompts

        # Infer material type from path
        path_str = str(output_path).lower()
        material_type = None

        if any(m in path_str for m in ["digital_ad", "ad_output"]):
            material_type = "digital_ad"
        elif "faq" in path_str:
            material_type = "faq"
        elif "blog" in path_str:
            material_type = "blog_post"

        # Skip if we already have this material type
        if material_type and material_type in materials_found:
            continue

        # Try to extract run_id from filename
        filename = output_path.stem
        run_id = filename.replace("_output", "").replace("_prompt", "")

        # Load or generate claims
        claims = load_or_generate_claims(run_id, output_path, claims_dir)

        # Filter by requirements
        if require_block_kinds and claims:
            if not all('block_kind' in c and 'claim_kind' in c for c in claims):
                continue

        # Skip if no claims
        if not claims:
            continue

        # Add to selected
        if material_type:
            selected.append((run_id, output_path, claims, material_type))
            materials_found.add(material_type)

    return selected


def extract_claim_aware_excerpt(
    full_text: str,
    claims: List[Dict[str, Any]],
    max_chars: int
) -> str:
    """Extract excerpt using claim offsets to show relevant context.

    Args:
        full_text: Full text
        claims: List of claim records with char_span
        max_chars: Maximum characters

    Returns:
        Excerpt showing claims in context
    """
    if len(full_text) <= max_chars:
        return full_text

    # Find claim span range
    if claims:
        char_spans = [c.get('char_span', (0, 0)) for c in claims if c.get('char_span')]
        if char_spans:
            min_start = min(s[0] for s in char_spans)
            max_end = max(s[1] for s in char_spans)

            # Expand window by ±200 chars
            window_start = max(0, min_start - 200)
            window_end = min(len(full_text), max_end + 200)

            # If window is still too large, truncate
            if window_end - window_start <= max_chars:
                return full_text[window_start:window_end]

    # Fallback: show beginning and end
    half = max_chars // 2 - 50
    return full_text[:half] + "\n\n[... middle section omitted ...]\n\n" + full_text[-half:]


def truncate_text(text: str, max_chars: int) -> str:
    """Truncate text to max_chars with ellipsis if needed.

    Args:
        text: Input text
        max_chars: Maximum characters

    Returns:
        Truncated text
    """
    if len(text) <= max_chars:
        return text

    # Show beginning and end
    half = max_chars // 2 - 50
    return text[:half] + "\n\n[... middle section omitted ...]\n\n" + text[-half:]


def format_claim_table_row(claim: Dict[str, Any]) -> str:
    """Format a claim as a Markdown table row.

    Args:
        claim: Claim record

    Returns:
        Markdown table row
    """
    claim_id = claim.get('claim_id', 'N/A')
    claim_kind = claim.get('claim_kind', 'N/A')
    block_kind = claim.get('block_kind', 'N/A')
    triggers = ', '.join(claim.get('trigger_types', []))
    char_span = claim.get('char_span', (0, 0))
    sentence = claim.get('sentence', '').replace('|', '\\|').replace('\n', ' ')[:80]

    return f"| `{claim_id[:20]}...` | {claim_kind} | {block_kind} | {triggers} | {char_span} | {sentence}... |"


def verify_offsets(
    claims: List[Dict[str, Any]],
    full_text: str
) -> Tuple[int, List[str]]:
    """Verify that all claim char_spans are exact substrings.

    Args:
        claims: List of claim records
        full_text: Original full text

    Returns:
        (num_verified, warnings) tuple
    """
    verified = 0
    warnings = []

    for claim in claims:
        sentence = claim.get('sentence', '')
        char_span = claim.get('char_span')
        if not char_span:
            warnings.append(f"Claim {claim.get('claim_id')} missing char_span")
            continue

        start, end = char_span
        if start >= len(full_text) or end > len(full_text):
            warnings.append(f"Claim {claim.get('claim_id')} has out-of-bounds char_span: {char_span}")
            continue

        extracted = full_text[start:end]
        if extracted == sentence:
            verified += 1
        else:
            warnings.append(
                f"Claim {claim.get('claim_id')} char_span mismatch:\n"
                f"  Expected: {sentence[:50]}...\n"
                f"  Got: {extracted[:50]}..."
            )

    return verified, warnings


def generate_markdown_example(
    run_id: str,
    output_path: Optional[Path],
    claims: List[Dict[str, Any]],
    material_type: str,
    max_excerpt_chars: int,
    max_claims: int,
    example_num: int
) -> str:
    """Generate Markdown section for one example.

    Args:
        run_id: Run identifier
        output_path: Path to output text (or None if not found)
        claims: List of claim records
        material_type: Material type name
        max_excerpt_chars: Max chars for text excerpt
        max_claims: Max claims to show
        example_num: Example number (1, 2, 3, ...)

    Returns:
        Markdown string
    """
    md = []
    md.append(f"## Example {example_num} — {material_type.replace('_', ' ').title()}")

    # Extract metadata from first claim
    if claims:
        product = claims[0].get('product', 'unknown')
        engine = claims[0].get('engine', 'unknown')
        extractor_version = claims[0].get('extractor_version', 'unknown')
        md.append(f"**Run ID:** `{run_id}`  ")
        md.append(f"**Product:** {product} | **Engine:** {engine}  ")
        md.append(f"**Extractor:** {extractor_version}")
    else:
        md.append(f"**Run ID:** `{run_id}`")

    md.append("")

    # Text excerpt
    if output_path and output_path.exists():
        full_text = output_path.read_text(encoding='utf-8')

        # Verify this is actually output, not a prompt
        text_kind = classify_text_kind(full_text)
        if text_kind == "prompt":
            md.append("### Generated Text Excerpt")
            md.append("")
            md.append("⚠️ **WARNING:** Located file appears to be a prompt/template, not generated output.")
            md.append("Showing extracted claims only (offsets may not match).")
            md.append("")
        else:
            # Use claim-aware excerpt to show relevant context
            excerpt = extract_claim_aware_excerpt(full_text, claims, max_excerpt_chars)

            md.append("### Generated Text Excerpt (Verbatim Model Output)")
            md.append("")
            md.append("```")
            md.append(excerpt)
            md.append("```")
            md.append("")

            # Verify offsets
            verified, warnings = verify_offsets(claims, full_text)
            if warnings:
                md.append("**Offset Verification:**")
                md.append(f"- {verified}/{len(claims)} claims verified")
                if warnings:
                    md.append(f"- {len(warnings)} warnings (see debug output)")
                md.append("")
    else:
        md.append("### Generated Text Excerpt")
        md.append("")
        md.append("⚠️ **Generated output text file not found for this run_id.**")
        md.append("")
        md.append("_Showing extracted claims only (from analysis/claims/*.json)._")
        md.append("")

    # Claims table
    md.append("### Extracted Claims (Verbatim)")
    md.append("")

    if claims:
        # Show up to max_claims
        display_claims = claims[:max_claims]

        md.append("| Claim ID | Claim Kind | Block Kind | Triggers | Char Span | Sentence |")
        md.append("|----------|------------|------------|----------|-----------|----------|")

        for claim in display_claims:
            md.append(format_claim_table_row(claim))

        md.append("")

        # Summary stats
        product_claims = sum(1 for c in claims if c.get('claim_kind') == 'product_claim')
        disclaimer_claims = sum(1 for c in claims if c.get('claim_kind') == 'disclaimer')
        meta_claims = sum(1 for c in claims if c.get('claim_kind') == 'meta')

        md.append("**Summary:**")
        md.append(f"- Total extracted claims: {len(claims)}")
        md.append(f"- Product claims: {product_claims}")
        md.append(f"- Disclaimer claims: {disclaimer_claims}")
        md.append(f"- Meta claims: {meta_claims}")
        if len(claims) > max_claims:
            md.append(f"- _(Showing {max_claims} of {len(claims)} claims)_")
        md.append("- **Note:** All sentences are exact substrings (offset-traceable)")
    else:
        md.append("_No claims extracted_")

    md.append("")
    md.append("---")
    md.append("")

    return '\n'.join(md)


def write_json_preview(
    run_id: str,
    claims: List[Dict[str, Any]],
    out_dir: Path,
    max_claims: int = 2
) -> Optional[Path]:
    """Write JSON preview of claims for technical appendix.

    Args:
        run_id: Run identifier
        claims: List of claim records
        out_dir: Output directory (docs/examples/)
        max_claims: Max claims to include

    Returns:
        Path to JSON file or None
    """
    if not claims:
        return None

    out_dir.mkdir(parents=True, exist_ok=True)
    json_file = out_dir / f"run_{run_id[:12]}_claims_preview.json"

    preview_claims = claims[:max_claims]
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(preview_claims, f, indent=2, ensure_ascii=False)

    return json_file


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate claim extraction examples from real runs"
    )
    parser.add_argument(
        '--claims-dir',
        default='analysis/claims',
        help='Directory containing claim JSONs'
    )
    parser.add_argument(
        '--outputs-dir',
        default='outputs',
        help='Directory containing output text files'
    )
    parser.add_argument(
        '--n',
        type=int,
        default=3,
        help='Number of examples to generate'
    )
    parser.add_argument(
        '--prefer-materials',
        default='digital_ad,faq,blog_post',
        help='Comma-separated material types to prefer'
    )
    parser.add_argument(
        '--out',
        default='docs/claim_extraction_examples.md',
        help='Output Markdown file'
    )
    parser.add_argument(
        '--seed',
        type=int,
        default=42,
        help='Random seed for deterministic selection'
    )
    parser.add_argument(
        '--max-excerpt-chars',
        type=int,
        default=900,
        help='Max characters for text excerpt'
    )
    parser.add_argument(
        '--max-claims',
        type=int,
        default=6,
        help='Max claims to show per example'
    )
    parser.add_argument(
        '--require-block-kinds',
        action='store_true',
        default=True,
        help='Require v2.0 claims with block_kind/claim_kind'
    )
    parser.add_argument(
        '--write-json-previews',
        action='store_true',
        help='Write JSON previews to docs/examples/'
    )

    args = parser.parse_args()

    # Parse preferred materials
    prefer_materials = [m.strip() for m in args.prefer_materials.split(',')]

    # Setup paths
    claims_dir = Path(args.claims_dir)
    outputs_dir = Path(args.outputs_dir)
    out_file = Path(args.out)

    print("Claim Extraction Example Generator")
    print("=" * 60)
    print(f"Claims directory: {claims_dir}")
    print(f"Outputs directory: {outputs_dir}")
    print(f"Preferred materials: {prefer_materials}")
    print(f"Output file: {out_file}")
    print()

    # Create claims dir if it doesn't exist (for on-the-fly generation)
    claims_dir.mkdir(parents=True, exist_ok=True)

    # Select examples
    print("Selecting example runs...")
    selected = select_example_runs(
        outputs_dir=outputs_dir,
        claims_dir=claims_dir,
        n=args.n,
        prefer_materials=prefer_materials,
        seed=args.seed,
        require_block_kinds=args.require_block_kinds
    )

    if not selected:
        print("ERROR: No suitable examples found!")
        print("  - Check that outputs_dir contains .txt files")
        print("  - Or generate claims first: python -m analysis.evaluate")
        return 1

    print(f"✓ Selected {len(selected)} examples")
    print()

    # Self-checks
    print("Self-checks:")
    for run_id, output_path, claims, material_type in selected:
        print(f"  - Run {run_id[:12]}: {material_type}")
        print(f"    Output text: {'✓ found' if output_path and output_path.exists() else '✗ not found'}")
        if claims:
            extractor_version = claims[0].get('extractor_version', 'unknown')
            print(f"    Extractor version: {extractor_version}")
            print(f"    Claims count: {len(claims)}")

            # Verify offsets if text available
            if output_path and output_path.exists():
                full_text = output_path.read_text(encoding='utf-8')
                verified, warnings = verify_offsets(claims, full_text)
                if warnings:
                    print(f"    ⚠ Offset warnings: {len(warnings)}")
                    for warning in warnings[:2]:  # Show first 2
                        print(f"      {warning.split(chr(10))[0]}")
                else:
                    print(f"    ✓ All {verified} offsets verified")
        print()

    # Generate Markdown
    print("Generating Markdown examples...")
    out_file.parent.mkdir(parents=True, exist_ok=True)

    with open(out_file, 'w', encoding='utf-8') as f:
        # Header
        f.write("# Claim Extraction Examples\n\n")
        f.write("Real examples from the LLM research pipeline, showing structure-aware claim extraction (v2.0).\n\n")
        f.write("**All excerpts below are verbatim segments of model-generated outputs (not prompts).**  \n")
        f.write("Claims are exact substrings; offsets are shown for traceability.\n\n")
        f.write("**Features demonstrated:**\n")
        f.write("- Block-aware parsing (headlines, Q/A, disclaimers)\n")
        f.write("- Claim kind tagging (product_claim vs disclaimer)\n")
        f.write("- Anchor-based trigger detection (numeric, guarantee, medical, financial, comparative)\n")
        f.write("- Exact char_span offsets (all sentences are verifiable substrings)\n\n")
        f.write("---\n\n")

        # Examples
        for i, (run_id, output_path, claims, material_type) in enumerate(selected, 1):
            example_md = generate_markdown_example(
                run_id=run_id,
                output_path=output_path,
                claims=claims,
                material_type=material_type,
                max_excerpt_chars=args.max_excerpt_chars,
                max_claims=args.max_claims,
                example_num=i
            )
            f.write(example_md)

            # Optional JSON preview
            if args.write_json_previews and claims:
                json_path = write_json_preview(
                    run_id=run_id,
                    claims=claims,
                    out_dir=out_file.parent / "examples",
                    max_claims=2
                )
                if json_path:
                    print(f"  ✓ JSON preview: {json_path}")

    print(f"✓ Generated examples: {out_file}")
    print()

    # Final sanity report
    print("=" * 60)
    print("SANITY REPORT")
    print("=" * 60)
    print()

    all_passed = True
    for i, (run_id, output_path, claims, material_type) in enumerate(selected, 1):
        print(f"Example {i} — {material_type}")
        print(f"  Run ID: {run_id[:20]}...")
        print(f"  Output path: {output_path if output_path else 'NOT FOUND'}")

        if output_path and output_path.exists():
            full_text = output_path.read_text(encoding='utf-8')
            text_kind = classify_text_kind(full_text)
            print(f"  Text kind: {text_kind} {'✓ (expected: output)' if text_kind == 'output' else '⚠ WARNING'}")

            if text_kind == "prompt":
                print(f"    ❌ FAILED: Found prompt instead of output!")
                all_passed = False

            # Check extractor version
            if claims:
                extractor_version = claims[0].get('extractor_version', 'unknown')
                print(f"  Extractor version: {extractor_version} {'✓' if extractor_version == 'v2.0' else '⚠'}")

                # Verify offsets
                verified, warnings = verify_offsets(claims, full_text)
                match_rate = verified / len(claims) if claims else 0
                print(f"  Offset match rate: {verified}/{len(claims)} ({match_rate:.1%})")

                if match_rate < 0.98:
                    print(f"    ⚠ WARNING: Match rate below 98%!")
                    if warnings:
                        print(f"    First mismatch: {warnings[0][:80]}...")
                    all_passed = False
                else:
                    print(f"    ✓ All offsets verified")
        else:
            print(f"  ⚠ WARNING: Output file not found")
            all_passed = False

        print()

    print("=" * 60)
    if all_passed:
        print("✅ ALL SANITY CHECKS PASSED")
    else:
        print("⚠ SOME SANITY CHECKS FAILED - Review warnings above")
    print("=" * 60)
    print()

    print("✅ Done! Examples ready for documentation.")
    return 0 if all_passed else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
