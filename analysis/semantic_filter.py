"""Semantic Pre-Filtering for Glass Box Audit.

Reduces false positives by pre-filtering relevant rules before NLI comparison.
Uses sentence embeddings to measure semantic similarity between claims and rules.

Goal: Reduce comparisons from ~750 to ~150 per file (80% reduction)
Expected FP reduction: 95% → 40-60%

Usage:
    from analysis.semantic_filter import SemanticFilter

    filter = SemanticFilter(top_k=5)
    relevant_rules = filter.filter_rules(claim, all_rules)
    # Now run NLI only on relevant_rules instead of all_rules
"""

import logging
from typing import List, Dict, Tuple
import torch
from sentence_transformers import SentenceTransformer, util

logger = logging.getLogger(__name__)


class SemanticFilter:
    """Embedding-based semantic pre-filter for claim-rule comparison."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", top_k: int = 5, similarity_threshold: float = 0.3):
        """Initialize semantic filter with embedding model.

        Args:
            model_name: Sentence-transformers model name
                - "all-MiniLM-L6-v2": Fast, 384-dim, 80MB (default)
                - "all-mpnet-base-v2": Better quality, 768-dim, 420MB
            top_k: Number of top rules to return per claim
            similarity_threshold: Minimum cosine similarity to include rule
        """
        self.model_name = model_name
        self.top_k = top_k
        self.similarity_threshold = similarity_threshold

        logger.info(f"Loading semantic filter model: {model_name}")
        self.model = SentenceTransformer(model_name)

        # Device detection (same as NLI model)
        if torch.cuda.is_available():
            self.device = torch.device("cuda")
        elif torch.backends.mps.is_available():
            self.device = torch.device("mps")
        else:
            self.device = torch.device("cpu")

        self.model.to(self.device)
        logger.info(f"Semantic filter loaded on device: {self.device}")

        # Cache for rule embeddings (avoid recomputing for same product)
        self._rule_cache: Dict[str, torch.Tensor] = {}

    def _get_cache_key(self, rules: List[str]) -> str:
        """Generate cache key from rule list."""
        # Use hash of concatenated rules as cache key
        return str(hash(tuple(sorted(rules))))

    def encode_rules(self, rules: List[str], cache_key: str = None) -> torch.Tensor:
        """Encode rules into embeddings with optional caching.

        Args:
            rules: List of rule strings to encode
            cache_key: Optional cache key (e.g., product_id)

        Returns:
            Tensor of shape (num_rules, embedding_dim)
        """
        # Check cache
        if cache_key and cache_key in self._rule_cache:
            logger.debug(f"Using cached embeddings for {cache_key}")
            return self._rule_cache[cache_key]

        # Encode rules
        embeddings = self.model.encode(
            rules,
            convert_to_tensor=True,
            device=self.device,
            show_progress_bar=False
        )

        # Cache for reuse
        if cache_key:
            self._rule_cache[cache_key] = embeddings
            logger.debug(f"Cached embeddings for {cache_key} ({len(rules)} rules)")

        return embeddings

    def filter_rules(
        self,
        claim: str,
        rules: List[str],
        rule_embeddings: torch.Tensor = None,
        cache_key: str = None
    ) -> List[Tuple[int, str, float]]:
        """Filter rules by semantic similarity to claim.

        Args:
            claim: Atomic claim string to compare
            rules: List of all rules to filter
            rule_embeddings: Pre-computed rule embeddings (optional)
            cache_key: Cache key for rule embeddings (optional)

        Returns:
            List of (rule_index, rule_text, similarity_score) tuples
            Sorted by similarity (highest first)
            Limited to top_k rules above similarity_threshold
        """
        # Encode claim
        claim_embedding = self.model.encode(
            claim,
            convert_to_tensor=True,
            device=self.device,
            show_progress_bar=False
        )

        # Get or compute rule embeddings
        if rule_embeddings is None:
            rule_embeddings = self.encode_rules(rules, cache_key=cache_key)

        # Compute cosine similarities
        similarities = util.cos_sim(claim_embedding, rule_embeddings)[0]

        # Get top-k indices above threshold
        scores, indices = torch.topk(similarities, k=min(self.top_k, len(rules)))

        # Filter by threshold and convert to list
        results = []
        for idx, score in zip(indices.cpu().numpy(), scores.cpu().numpy()):
            if float(score) >= self.similarity_threshold:
                results.append((int(idx), rules[int(idx)], float(score)))

        logger.debug(
            f"Claim: '{claim[:50]}...' -> {len(results)}/{len(rules)} rules "
            f"(threshold={self.similarity_threshold})"
        )

        return results

    def filter_rules_batch(
        self,
        claims: List[str],
        rules: List[str],
        cache_key: str = None
    ) -> List[List[Tuple[int, str, float]]]:
        """Filter rules for multiple claims in batch (faster).

        Args:
            claims: List of claim strings
            rules: List of all rules
            cache_key: Cache key for rule embeddings

        Returns:
            List of filtered rule lists (one per claim)
        """
        # Encode all claims and rules
        claim_embeddings = self.model.encode(
            claims,
            convert_to_tensor=True,
            device=self.device,
            show_progress_bar=False,
            batch_size=32
        )

        rule_embeddings = self.encode_rules(rules, cache_key=cache_key)

        # Compute similarity matrix (claims × rules)
        similarity_matrix = util.cos_sim(claim_embeddings, rule_embeddings)

        # Filter for each claim
        results = []
        for i, claim in enumerate(claims):
            similarities = similarity_matrix[i]

            # Get top-k indices above threshold
            scores, indices = torch.topk(similarities, k=min(self.top_k, len(rules)))

            claim_results = []
            for idx, score in zip(indices.cpu().numpy(), scores.cpu().numpy()):
                if float(score) >= self.similarity_threshold:
                    claim_results.append((int(idx), rules[int(idx)], float(score)))

            results.append(claim_results)

        logger.info(
            f"Batch filtered {len(claims)} claims -> "
            f"avg {sum(len(r) for r in results)/len(results):.1f} rules per claim"
        )

        return results

    def get_stats(self) -> Dict:
        """Get statistics about filtering performance."""
        return {
            'model_name': self.model_name,
            'top_k': self.top_k,
            'similarity_threshold': self.similarity_threshold,
            'device': str(self.device),
            'cached_products': len(self._rule_cache)
        }


def estimate_reduction(num_claims: int, num_rules: int, top_k: int = 5) -> Dict:
    """Estimate comparison reduction from semantic filtering.

    Args:
        num_claims: Number of claims extracted from document
        num_rules: Total number of rules in product YAML
        top_k: Number of rules to keep per claim

    Returns:
        Dictionary with reduction statistics
    """
    comparisons_before = num_claims * num_rules
    comparisons_after = num_claims * min(top_k, num_rules)
    reduction_pct = (1 - comparisons_after / comparisons_before) * 100

    return {
        'claims': num_claims,
        'rules': num_rules,
        'comparisons_before': comparisons_before,
        'comparisons_after': comparisons_after,
        'reduction_pct': reduction_pct,
        'top_k': top_k
    }


# Example usage and testing
if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(level=logging.INFO)

    # Example rules (product specs)
    rules = [
        "Screen size is 6.3 inches",
        "Camera is 50 megapixels",
        "Storage options are 128GB, 256GB, or 512GB",
        "Battery capacity is 4700-5000 mAh",
        "NOT FDA approved as a drug",
        "Contains 3mg melatonin per tablet",
        "Wireless charging is NOT supported",
        "Block time is approximately 5 seconds",
        "Smart contract execution requires gas fees",
        "Staking rewards are variable and NOT guaranteed"
    ]

    # Example claims
    claims = [
        "The phone has a 6.5 inch display",  # Similar to rule 0 (screen size)
        "This supplement is FDA approved",   # Similar to rule 4 (FDA)
        "Staking rewards are fixed at 10%",  # Similar to rule 9 (staking)
        "The camera quality is amazing"      # Generic, low similarity to all
    ]

    # Initialize filter
    filter = SemanticFilter(top_k=3, similarity_threshold=0.3)

    # Test single claim filtering
    print("\n=== Single Claim Filtering ===")
    for claim in claims:
        print(f"\nClaim: '{claim}'")
        relevant_rules = filter.filter_rules(claim, rules)
        for idx, rule, score in relevant_rules:
            print(f"  [{score:.3f}] Rule {idx}: {rule[:60]}")

    # Test batch filtering
    print("\n=== Batch Filtering ===")
    batch_results = filter.filter_rules_batch(claims, rules)
    for i, (claim, relevant_rules) in enumerate(zip(claims, batch_results)):
        print(f"\nClaim {i}: '{claim}'")
        print(f"  Filtered to {len(relevant_rules)}/{len(rules)} rules")

    # Estimate reduction
    print("\n=== Reduction Estimate ===")
    stats = estimate_reduction(num_claims=30, num_rules=25, top_k=5)
    print(f"Claims: {stats['claims']}")
    print(f"Rules: {stats['rules']}")
    print(f"Comparisons before: {stats['comparisons_before']}")
    print(f"Comparisons after: {stats['comparisons_after']}")
    print(f"Reduction: {stats['reduction_pct']:.1f}%")
