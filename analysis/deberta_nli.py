"""DeBERTa-based NLI (Natural Language Inference) verifier.

Uses pretrained DeBERTa models fine-tuned on MNLI (Multi-Genre NLI) to verify
whether extracted claims are:
- ENTAILMENT: Supported by ground truth (authorized)
- CONTRADICTION: Contradicted by ground truth (violation)
- NEUTRAL: Not supported or contradicted (unsupported/unknown)

This is INFERENCE-ONLY (V1). No training or fine-tuning happens here.
"""

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import hashlib
from typing import Dict, Any


def hash_text(text: str) -> str:
    """Generate short SHA256 hash for text deduplication."""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:12]


class DebertaNliVerifier:
    """DeBERTa-based NLI verifier for claim verification.

    Uses a pretrained DeBERTa model fine-tuned on MNLI to classify
    the relationship between premise (ground truth) and hypothesis (claim).

    Attributes:
        model_name: HuggingFace model identifier
        device: 'cpu' or 'cuda'
        tokenizer: HuggingFace tokenizer
        model: HuggingFace model
        label_map: Mapping from model output indices to canonical labels
    """

    def __init__(
        self,
        model_name: str = "microsoft/deberta-v3-base",
        device: str = "cpu"
    ):
        """Initialize DeBERTa NLI verifier.

        Args:
            model_name: HuggingFace model identifier
                Default: microsoft/deberta-v3-base (general-purpose)
                For MNLI-specific: "microsoft/deberta-v3-base-mnli" or
                                   "cross-encoder/nli-deberta-v3-base"
            device: Device to run inference on ('cpu' or 'cuda')

        Note:
            The model must be a sequence classification model with 3 labels
            (entailment, neutral, contradiction). Label order may vary by
            checkpoint, so we detect it from config.id2label.
        """
        self.model_name = model_name
        self.device = device

        print(f"Loading DeBERTa NLI model: {model_name}")
        print(f"Device: {device}")

        # Load tokenizer and model
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
        self.model.to(device)
        self.model.eval()  # Set to evaluation mode

        # Detect label mapping from model config
        self.label_map = self._build_label_map()
        print(f"Label mapping: {self.label_map}")

    def _build_label_map(self) -> Dict[int, str]:
        """Build label mapping from model config.

        Different checkpoints may use different label orders:
        - Some: 0=entailment, 1=neutral, 2=contradiction
        - Others: 0=contradiction, 1=neutral, 2=entailment

        Returns:
            Dict mapping model output index to canonical label
        """
        # Get label mapping from model config
        id2label = self.model.config.id2label

        # Normalize labels to lowercase
        label_map = {int(idx): label.lower() for idx, label in id2label.items()}

        # Verify we have all 3 expected labels
        expected_labels = {"entailment", "neutral", "contradiction"}
        actual_labels = set(label_map.values())

        if not expected_labels.issubset(actual_labels):
            # Fallback: assume standard order
            print(f"Warning: Unexpected labels {actual_labels}, using fallback mapping")
            label_map = {0: "entailment", 1: "neutral", 2: "contradiction"}

        return label_map

    def verify(self, premise: str, hypothesis: str) -> Dict[str, Any]:
        """Verify hypothesis against premise using NLI.

        Args:
            premise: Ground truth text (from product YAML)
            hypothesis: Claim sentence to verify

        Returns:
            Dict with:
                - model: Model name
                - label: One of 'entailment', 'neutral', 'contradiction'
                - probs: Dict of {label: probability} for all 3 labels
                - premise_hash: Hash of premise text
                - hypothesis_hash: Hash of hypothesis text

        Example:
            >>> verifier = DebertaNliVerifier()
            >>> result = verifier.verify(
            ...     premise="AUTHORIZED:\\n- 120 Hz display.",
            ...     hypothesis="Experience 120 Hz display."
            ... )
            >>> result['label'] in ['entailment', 'neutral', 'contradiction']
            True
            >>> abs(sum(result['probs'].values()) - 1.0) < 0.01
            True
        """
        # Tokenize premise-hypothesis pair
        inputs = self.tokenizer(
            premise,
            hypothesis,
            truncation=True,
            max_length=256,
            padding=True,
            return_tensors="pt"
        )

        # Move to device
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        # Run inference
        with torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits
            probs = torch.softmax(logits, dim=-1)[0]  # [num_labels]

        # Get predicted label
        pred_idx = torch.argmax(probs).item()
        pred_label = self.label_map[pred_idx]

        # Build probability dict for all labels
        probs_dict = {
            self.label_map[idx]: float(probs[idx].item())
            for idx in range(len(probs))
        }

        return {
            "model": self.model_name,
            "label": pred_label,
            "probs": probs_dict,
            "premise_hash": hash_text(premise),
            "hypothesis_hash": hash_text(hypothesis)
        }

    def verify_batch(self, premise: str, hypotheses: list) -> list:
        """Verify multiple hypotheses against same premise (batch mode).

        Args:
            premise: Ground truth text
            hypotheses: List of claim sentences

        Returns:
            List of verification results (one per hypothesis)
        """
        return [self.verify(premise, hyp) for hyp in hypotheses]


# Self-check
if __name__ == "__main__":
    print("DeBERTa NLI Verifier Self-Check")
    print("=" * 60)

    # Check if running on CPU or CUDA
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")

    # Initialize verifier with a lightweight MNLI model
    # Using cross-encoder model which is specifically trained for NLI
    try:
        verifier = DebertaNliVerifier(
            model_name="cross-encoder/nli-deberta-v3-small",  # Smaller, faster
            device=device
        )
        print("✓ Model loaded successfully")
    except Exception as e:
        print(f"✗ Model loading failed: {e}")
        print("Trying fallback model...")
        verifier = DebertaNliVerifier(
            model_name="microsoft/deberta-v3-small",
            device=device
        )

    # Test case 1: Entailment (claim matches authorized)
    premise1 = """AUTHORIZED:
- 120 Hz display for smoother on-screen motion.
- 5G connectivity where available.

PROHIBITED:
- Guaranteed to work for all users.

SPECS:
- Display: 6.5 in, 120 Hz

DISCLAIMERS:
- Battery life varies by usage."""

    hypothesis1 = "Experience 120 Hz display for smoother motion."

    result1 = verifier.verify(premise1, hypothesis1)
    print("\n--- Test 1: Expected ENTAILMENT ---")
    print(f"Hypothesis: {hypothesis1}")
    print(f"Label: {result1['label']}")
    print(f"Probs: {result1['probs']}")

    # Test case 2: Contradiction (claim violates prohibited)
    hypothesis2 = "Guaranteed to work for all users without fail."

    result2 = verifier.verify(premise1, hypothesis2)
    print("\n--- Test 2: Expected CONTRADICTION ---")
    print(f"Hypothesis: {hypothesis2}")
    print(f"Label: {result2['label']}")
    print(f"Probs: {result2['probs']}")

    # Test case 3: Neutral (claim not mentioned)
    hypothesis3 = "This device comes in multiple colors."

    result3 = verifier.verify(premise1, hypothesis3)
    print("\n--- Test 3: Expected NEUTRAL ---")
    print(f"Hypothesis: {hypothesis3}")
    print(f"Label: {result3['label']}")
    print(f"Probs: {result3['probs']}")

    # Verify output schema
    print("\n--- Schema Validation ---")
    required_keys = {"model", "label", "probs", "premise_hash", "hypothesis_hash"}
    if required_keys.issubset(result1.keys()):
        print(f"✓ All required keys present: {required_keys}")
    else:
        print(f"✗ Missing keys: {required_keys - set(result1.keys())}")

    # Verify label is valid
    valid_labels = {"entailment", "neutral", "contradiction"}
    if result1["label"] in valid_labels:
        print(f"✓ Label is valid: {result1['label']}")
    else:
        print(f"✗ Invalid label: {result1['label']}")

    # Verify probs sum to ~1
    prob_sum = sum(result1["probs"].values())
    if abs(prob_sum - 1.0) < 0.01:
        print(f"✓ Probabilities sum to ~1.0: {prob_sum:.4f}")
    else:
        print(f"✗ Probabilities don't sum to 1: {prob_sum:.4f}")

    # Verify hashes are 12 chars
    if len(result1["premise_hash"]) == 12:
        print(f"✓ Premise hash is 12 chars: {result1['premise_hash']}")
    else:
        print(f"✗ Premise hash wrong length: {result1['premise_hash']}")

    print("\n" + "=" * 60)
    print("Self-check complete!")
