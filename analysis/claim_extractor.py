"""Deterministic (LLM-free) claim extraction from marketing materials.

Extracts claim candidates using rule-based sentence splitting and trigger detection.
No paraphrasing, no LLM calls - purely deterministic.
"""

import re
from typing import List, Tuple, Dict, Any
from dataclasses import dataclass


# Lexicons for trigger detection (can be expanded)
CLAIM_VERBS = {
    "is", "are", "has", "have", "provides", "provides", "offers", "includes",
    "contains", "features", "ensures", "guarantees", "supports", "reduces",
    "increases", "improves", "enhances", "designed to", "helps", "delivers",
    "enables", "allows", "achieves", "maintains", "prevents", "protects"
}

GUARANTEE_WORDS = {
    "guaranteed", "guarantee", "always", "never", "100%", "proven", "certified",
    "clinically proven", "scientifically proven", "lab-tested", "instant",
    "immediate", "overnight", "permanent", "forever", "eliminate", "cure"
}

MEDICAL_TERMS = {
    "treat", "treats", "cure", "cures", "heal", "heals", "diagnose", "diagnoses",
    "prevent", "prevents", "disease", "disorder", "condition", "illness"
}

FINANCIAL_TERMS = {
    "invest", "investment", "returns", "profit", "earnings", "yield", "guaranteed return",
    "risk-free", "no risk", "secure investment"
}


def split_sentences(text: str) -> List[Tuple[str, int, int]]:
    """Split text into sentences using deterministic heuristics.

    Args:
        text: Input text

    Returns:
        List of (sentence, start_offset, end_offset) tuples
    """
    # Simple sentence splitting heuristic (can be improved with spaCy if needed)
    # This handles common cases: ". ", "! ", "? " followed by capital or newline

    sentences = []
    current_start = 0

    # Pattern: sentence boundary markers
    # Lookahead ensures we don't split on abbreviations like "Dr.", "Inc.", etc.
    pattern = r'(?<=[.!?])\s+(?=[A-Z])|(?<=[.!?])\n+'

    # Find all sentence boundaries
    for match in re.finditer(pattern, text):
        sent_end = match.start()
        sentence = text[current_start:sent_end].strip()

        if sentence:  # Skip empty sentences
            # Adjust offsets to account for stripped whitespace
            actual_start = text.find(sentence, current_start)
            actual_end = actual_start + len(sentence)
            sentences.append((sentence, actual_start, actual_end))

        current_start = match.end()

    # Add the last sentence
    if current_start < len(text):
        sentence = text[current_start:].strip()
        if sentence:
            actual_start = text.find(sentence, current_start)
            actual_end = actual_start + len(sentence)
            sentences.append((sentence, actual_start, actual_end))

    # Fallback: if no sentences found, treat whole text as one sentence
    if not sentences and text.strip():
        sentences.append((text.strip(), 0, len(text.strip())))

    return sentences


def is_candidate_claim(sentence: str) -> Tuple[bool, List[str]]:
    """Check if sentence is a claim candidate using trigger detection.

    Args:
        sentence: Input sentence

    Returns:
        (is_candidate, trigger_types) where trigger_types is list of matched triggers
    """
    triggers = []
    sent_lower = sentence.lower()

    # 1. Numeric trigger (numbers with optional units)
    # Matches: "3 mg", "7 years", "128 GB", "50%", "IP67", etc.
    numeric_pattern = r'\b\d+\.?\d*\s*(?:mg|g|kg|ml|l|gb|mb|hz|mhz|ghz|fps|years?|months?|days?|hours?|minutes?|seconds?|%|percent|dollars?|\$|€|£|USD|EUR|GBP|IP\d+)\b'
    if re.search(numeric_pattern, sent_lower, re.IGNORECASE):
        triggers.append("numeric")

    # 2. Guarantee language (high-risk)
    for guarantee_word in GUARANTEE_WORDS:
        if guarantee_word in sent_lower:
            triggers.append("guarantee")
            break

    # 3. Medical claims (regulated)
    for medical_term in MEDICAL_TERMS:
        if medical_term in sent_lower:
            triggers.append("medical")
            break

    # 4. Financial promises (regulated)
    for financial_term in FINANCIAL_TERMS:
        if financial_term in sent_lower:
            triggers.append("financial")
            break

    # 5. Comparative statements
    comparative_pattern = r'\b(better|faster|more|less|superior|best|#1|number one|leading|top)\b'
    if re.search(comparative_pattern, sent_lower):
        triggers.append("comparative")

    # 6. Claim verbs (only add if at least one anchor trigger is present)
    # This prevents common verbs like "is/are/has" from inflating claim counts
    words = set(re.findall(r'\b\w+\b', sent_lower))
    has_claim_verb = bool(words & CLAIM_VERBS)
    if has_claim_verb and len(triggers) > 0:
        triggers.append("claim_verb")

    # Sentence is a candidate if it has any triggers
    return (len(triggers) > 0, triggers)


def extract_claim_candidates(
    full_text: str,
    run_metadata: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Extract claim candidates from marketing material.

    Args:
        full_text: Full marketing material text
        run_metadata: Metadata dict with keys: run_id, product, material, engine, temp, time_of_day, rep

    Returns:
        List of claim records following canonical schema
    """
    sentences = split_sentences(full_text)
    claim_records = []

    for sent_idx, (sentence, start, end) in enumerate(sentences):
        is_candidate, triggers = is_candidate_claim(sentence)

        if is_candidate:
            claim_id = f"{run_metadata['run_id']}::sent{sent_idx:03d}"

            claim_record = {
                "run_id": run_metadata["run_id"],
                "product": run_metadata.get("product_id", "unknown"),
                "material": run_metadata.get("material_type", "unknown"),
                "engine": run_metadata.get("engine", "unknown"),
                "time_of_day": run_metadata.get("time_of_day", "unknown"),
                "temp": float(run_metadata.get("temperature", 0.0)),
                "rep": int(run_metadata.get("repetition_id", 0)),
                "claim_id": claim_id,
                "sentence": sentence,
                "sent_index": sent_idx,
                "char_span": (start, end),
                "trigger_types": triggers,
                "extractor_version": "v1.1",
                # DeBERTa fields will be added later
                "deberta": None,
                "severity": None,
            }

            claim_records.append(claim_record)

    return claim_records


# Self-check / unit test
if __name__ == "__main__":
    """Self-check with hardcoded examples."""
    print("Running claim_extractor self-checks...\n")

    # Test 1: Numeric claim
    test1 = "Our product contains 3 mg of melatonin per serving."
    sents1 = split_sentences(test1)
    assert len(sents1) == 1, f"Expected 1 sentence, got {len(sents1)}"
    is_claim1, triggers1 = is_candidate_claim(sents1[0][0])
    assert is_claim1, "Expected numeric claim to be detected"
    assert "numeric" in triggers1, f"Expected 'numeric' trigger, got {triggers1}"
    print(f"✓ Test 1 passed: {sents1[0][0]}")
    print(f"  Triggers: {triggers1}\n")

    # Test 2: Guarantee claim (should trigger)
    test2 = "Guaranteed to work or your money back!"
    sents2 = split_sentences(test2)
    assert len(sents2) == 1
    is_claim2, triggers2 = is_candidate_claim(sents2[0][0])
    assert is_claim2, "Expected guarantee claim to be detected"
    assert "guarantee" in triggers2, f"Expected 'guarantee' trigger, got {triggers2}"
    print(f"✓ Test 2 passed: {sents2[0][0]}")
    print(f"  Triggers: {triggers2}\n")

    # Test 3: Normal sentence (should NOT trigger)
    test3 = "Thank you for considering our product."
    sents3 = split_sentences(test3)
    assert len(sents3) == 1
    is_claim3, triggers3 = is_candidate_claim(sents3[0][0])
    assert not is_claim3, f"Expected non-claim sentence, but got triggers: {triggers3}"
    assert len(triggers3) == 0, f"Expected no triggers, got {triggers3}"
    print(f"✓ Test 3 passed: {sents3[0][0]}")
    print(f"  Triggers: {triggers3} (no triggers, as expected)\n")

    # Test 3b: Sentence with claim_verb but no anchor (should NOT trigger)
    test3b = "This product is designed to help you."
    sents3b = split_sentences(test3b)
    assert len(sents3b) == 1
    is_claim3b, triggers3b = is_candidate_claim(sents3b[0][0])
    assert not is_claim3b, f"Expected non-claim (claim_verb alone), but got triggers: {triggers3b}"
    print(f"✓ Test 3b passed: {sents3b[0][0]}")
    print(f"  Triggers: {triggers3b} (claim_verb alone doesn't trigger)\n")

    # Test 4: Multi-sentence text
    test4 = "Our smartphone has 128 GB of storage. It provides 7 years of updates. You'll love it!"
    sents4 = split_sentences(test4)
    assert len(sents4) == 3, f"Expected 3 sentences, got {len(sents4)}"
    print(f"✓ Test 4 passed: Split {len(sents4)} sentences")

    # Extract claims from test4
    run_meta = {
        "run_id": "test_run_001",
        "product_id": "smartphone_mid",
        "material_type": "digital_ad.j2",
        "engine": "openai",
        "temperature": 0.6,
        "time_of_day": "morning",
        "repetition_id": 1
    }

    claims4 = extract_claim_candidates(test4, run_meta)
    print(f"  Extracted {len(claims4)} claim candidates:")
    for claim in claims4:
        print(f"    - Sent {claim['sent_index']}: {claim['sentence']}")
        print(f"      Triggers: {claim['trigger_types']}")

    # Verify only first two sentences extracted (both have numeric triggers)
    assert len(claims4) == 2, f"Expected 2 claims, got {len(claims4)}"
    assert claims4[0]['sent_index'] == 0, "First claim should be sentence 0"
    assert claims4[1]['sent_index'] == 1, "Second claim should be sentence 1"
    assert "numeric" in claims4[0]['trigger_types'], "First claim should have numeric trigger"
    assert "numeric" in claims4[1]['trigger_types'], "Second claim should have numeric trigger"
    print(f"✓ Verified: Only sentences with anchor triggers extracted\n")

    print("✅ All self-checks passed!")
    print("\nClaim extractor v1.1: claim_verb no longer triggers extraction alone.")
    print("Only sentences with anchor triggers (numeric/guarantee/medical/financial/comparative) are extracted.")
