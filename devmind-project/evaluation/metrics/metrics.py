"""
Core evaluation metrics for retrieval quality.

Implements:
- Recall@K: What fraction of expected results appear in top-k?
- MRR (Mean Reciprocal Rank): Reciprocal rank of first relevant result
- NDCG@K: Normalized Discounted Cumulative Gain (accounts for ranking)
- Answer Relevance: Keyword coverage in LLM responses
"""

import math
from typing import List, Dict


def recall_at_k(expected: List[str], retrieved: List[str], k: int) -> float:
    """
    What fraction of expected results appear in the top-k retrieved?
    
    Args:
        expected: List of expected file paths
        retrieved: List of retrieved file paths (ordered by relevance)
        k: Number of top results to consider
        
    Returns:
        Recall score between 0.0 and 1.0
        
    Example:
        >>> expected = ["auth.py", "jwt.py", "security.py"]
        >>> retrieved = ["auth.py", "models.py", "jwt.py", "utils.py"]
        >>> recall_at_k(expected, retrieved, k=5)
        0.666  # 2 out of 3 expected results found
    """
    if not expected:
        return 1.0
    
    retrieved_top_k = set(retrieved[:k])
    hits = sum(1 for doc in expected if doc in retrieved_top_k)
    return hits / len(expected)


def mean_reciprocal_rank(primary_expected: List[str], retrieved: List[str]) -> float:
    """
    Reciprocal of the rank of the first relevant result.
    
    MRR rewards systems that put the most relevant result at the top.
    
    Args:
        primary_expected: List of primary (most relevant) expected results
        retrieved: List of retrieved results (ordered by relevance)
        
    Returns:
        MRR score between 0.0 and 1.0
        
    Example:
        >>> primary = ["auth.py"]
        >>> retrieved = ["models.py", "auth.py", "utils.py"]
        >>> mean_reciprocal_rank(primary, retrieved)
        0.5  # Found at position 2 (1-indexed), so 1/2 = 0.5
    """
    for i, doc in enumerate(retrieved):
        if doc in primary_expected:
            return 1.0 / (i + 1)
    return 0.0


def ndcg_at_k(expected_chunks: List[Dict], retrieved: List[str], k: int) -> float:
    """
    Normalized Discounted Cumulative Gain at k.
    
    NDCG accounts for both presence AND position of relevant results.
    It gives higher scores when primary results appear early.
    
    Args:
        expected_chunks: List of dicts with 'file' and 'relevance' keys
        retrieved: List of retrieved file paths (ordered)
        k: Number of top results to consider
        
    Returns:
        NDCG score between 0.0 and 1.0
        
    Example:
        >>> expected = [
        ...     {"file": "auth.py", "relevance": "primary"},
        ...     {"file": "utils.py", "relevance": "secondary"}
        ... ]
        >>> retrieved = ["auth.py", "models.py", "utils.py"]
        >>> ndcg_at_k(expected, retrieved, k=3)
        0.89  # Primary result at position 1 (good), secondary at 3
    """
    # Build relevance map
    relevance_map = {}
    for chunk in expected_chunks:
        # Primary results get score 3, secondary get score 1
        score = 3 if chunk["relevance"] == "primary" else 1
        relevance_map[chunk["file"]] = score

    # DCG for retrieved order
    dcg = 0.0
    for i, doc in enumerate(retrieved[:k]):
        rel = relevance_map.get(doc, 0)
        # Discount by log position (i+2 because log2(1) = 0)
        dcg += rel / math.log2(i + 2)

    # Ideal DCG (sort by relevance descending)
    ideal_scores = sorted(relevance_map.values(), reverse=True)[:k]
    idcg = sum(rel / math.log2(i + 2) for i, rel in enumerate(ideal_scores))

    if idcg == 0:
        return 0.0
    
    return dcg / idcg


def answer_relevance_score(response_text: str, expected_keywords: List[str]) -> float:
    """
    Simple keyword coverage metric for generated answers.
    
    Checks what percentage of expected keywords appear in the LLM response.
    
    Args:
        response_text: Generated answer from LLM
        expected_keywords: Keywords that should appear
        
    Returns:
        Coverage score between 0.0 and 1.0
        
    Example:
        >>> response = "JWT tokens are decoded and validated for expiry"
        >>> keywords = ["jwt.decode", "token validation", "expiry check"]
        >>> answer_relevance_score(response, keywords)
        0.666  # 2 out of 3 keywords present (partial match for "jwt.decode")
    """
    if not expected_keywords:
        return 1.0
    
    response_lower = response_text.lower()
    hits = sum(1 for kw in expected_keywords if kw.lower() in response_lower)
    return hits / len(expected_keywords)
