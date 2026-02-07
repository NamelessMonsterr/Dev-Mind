"""
Evaluation engine for the golden dataset.

Runs queries through the retrieval pipeline and compares results
against expected chunks to produce quality metrics.
"""

from dataclasses import dataclass
from pathlib import Path
import json
import time
from typing import Optional, List
import logging

from evaluation.metrics.metrics import (
    recall_at_k,
    mean_reciprocal_rank,
    ndcg_at_k,
    answer_relevance_score,
)

logger = logging.getLogger(__name__)


@dataclass
class EvalResult:
    """Results for a single query evaluation."""
    query_id: str
    query: str
    recall_at_5: float
    recall_at_10: float
    mrr: float
    ndcg_at_10: float
    latency_ms: float
    retrieved_files: List[str]
    expected_files: List[str]
    hit: bool  # Was the primary result found in top 5?


@dataclass
class EvalSummary:
    """Aggregated evaluation results across all queries."""
    total_queries: int
    mean_recall_at_5: float
    mean_recall_at_10: float
    mean_mrr: float
    mean_ndcg_at_10: float
    p50_latency_ms: float
    p95_latency_ms: float
    hit_rate: float  # % of queries where primary result was in top 5
    failures: List[EvalResult]  # Queries that scored 0


class RetrievalEvaluator:
    """Runs golden dataset against the retrieval pipeline and produces metrics."""

    def __init__(self, search_client, dataset_path: str):
        """
        Initialize evaluator.
        
        Args:
            search_client: Client with search(query, top_k) method
            dataset_path: Path to golden dataset JSONL file
        """
        self.search_client = search_client
        self.dataset = self._load_dataset(dataset_path)
        logger.info(f"Loaded {len(self.dataset)} queries from {dataset_path}")

    def _load_dataset(self, path: str) -> List[dict]:
        """Load queries from JSONL file."""
        entries = []
        with open(path, "r") as f:
            for line in f:
                if line.strip():
                    entries.append(json.loads(line))
        return entries

    async def evaluate(
        self, k: int = 10, collection: Optional[str] = None
    ) -> EvalSummary:
        """
        Run evaluation on entire dataset.
        
        Args:
            k: Number of top results to retrieve
            collection: Optional Qdrant collection name
            
        Returns:
            Aggregated evaluation summary
        """
        results: List[EvalResult] = []

        logger.info(f"Starting evaluation with top_k={k}")
        for entry in self.dataset:
            result = await self._evaluate_single(entry, k, collection)
            results.append(result)
            
            if result.recall_at_10 == 0.0:
                logger.warning(f"Failed query [{result.query_id}]: {result.query}")

        return self._summarize(results)

    async def _evaluate_single(
        self, entry: dict, k: int, collection: Optional[str]
    ) -> EvalResult:
        """Evaluate a single query."""
        expected_files = [chunk["file"] for chunk in entry["expected_chunks"]]
        primary_files = [
            chunk["file"]
            for chunk in entry["expected_chunks"]
            if chunk["relevance"] == "primary"
        ]

        # Run search and measure latency
        start = time.perf_counter()
        try:
            search_results = await self.search_client.search(
                query=entry["query"], top_k=k, collection=collection
            )
            latency_ms = (time.perf_counter() - start) * 1000
        except Exception as e:
            logger.error(f"Search failed for [{entry['id']}]: {e}")
            latency_ms = 0
            search_results = []

        # Extract file paths from results
        retrieved_files = [r.file_path for r in search_results] if search_results else []

        # Compute metrics
        return EvalResult(
            query_id=entry["id"],
            query=entry["query"],
            recall_at_5=recall_at_k(expected_files, retrieved_files, k=5),
            recall_at_10=recall_at_k(expected_files, retrieved_files, k=10),
            mrr=mean_reciprocal_rank(primary_files, retrieved_files),
            ndcg_at_10=ndcg_at_k(entry["expected_chunks"], retrieved_files, k=10),
            latency_ms=latency_ms,
            retrieved_files=retrieved_files[:k],
            expected_files=expected_files,
            hit=any(f in retrieved_files[:5] for f in primary_files),
        )

    def _summarize(self, results: List[EvalResult]) -> EvalSummary:
        """Aggregate results into summary statistics."""
        import statistics

        latencies = sorted([r.latency_ms for r in results])
        n = len(results)
        failures = [r for r in results if r.recall_at_10 == 0.0]

        return EvalSummary(
            total_queries=n,
            mean_recall_at_5=statistics.mean(r.recall_at_5 for r in results),
            mean_recall_at_10=statistics.mean(r.recall_at_10 for r in results),
            mean_mrr=statistics.mean(r.mrr for r in results),
            mean_ndcg_at_10=statistics.mean(r.ndcg_at_10 for r in results),
            p50_latency_ms=latencies[n // 2] if latencies else 0,
            p95_latency_ms=latencies[int(n * 0.95)] if latencies else 0,
            hit_rate=sum(1 for r in results if r.hit) / n if n > 0 else 0,
            failures=failures,
        )
