"""
CLI tool to run retrieval evaluation on golden dataset.

Usage:
    python -m evaluation.scripts.run_eval --label baseline
    python -m evaluation.scripts.run_eval --collection bge_large --label bge_test
"""

import asyncio
import argparse
import json
from datetime import datetime
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from evaluation.metrics.evaluator import RetrievalEvaluator


def print_summary(summary, run_label: str) -> None:
    """Print evaluation summary to console."""
    print(f"\n{'=' * 60}")
    print(f"  EVALUATION REPORT: {run_label}")
    print(f"  {datetime.now().isoformat()}")
    print(f"{'=' * 60}\n")

    print(f"  Queries Evaluated:  {summary.total_queries}")
    print(f"  Hit Rate (top 5):   {summary.hit_rate:.1%}")
    print(f"  Mean Recall@5:      {summary.mean_recall_at_5:.3f}")
    print(f"  Mean Recall@10:     {summary.mean_recall_at_10:.3f}")
    print(f"  Mean MRR:           {summary.mean_mrr:.3f}")
    print(f"  Mean NDCG@10:       {summary.mean_ndcg_at_10:.3f}")
    print(f"  Latency P50:        {summary.p50_latency_ms:.0f}ms}")
    print(f"  Latency P95:        {summary.p95_latency_ms:.0f}ms")

    target_recall = 0.80
    status = "✅ PASS" if summary.mean_recall_at_10 >= target_recall else "❌ FAIL"
    print(f"\n  Recall@10 vs Target (≥{target_recall:.0%}): {status}")

    if summary.failures:
        print(f"\n  ⚠️  Failed Queries ({len(summary.failures)}):")
        for f in summary.failures[:5]:
            print(f"    • [{f.query_id}] \"{f.query}\"")
            print(f"      Expected: {f.expected_files}")
            print(f"      Got:      {f.retrieved_files[:3]}")

    print(f"\n{'=' * 60}\n")


def save_results(summary, run_label: str, args) -> Path:
    """Save evaluation results to JSON file."""
    output_dir = Path("evaluation/results")
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"eval_{run_label}_{timestamp}.json"

    data = {
        "run_label": run_label,
        "timestamp": datetime.now().isoformat(),
        "config": {
            "dataset": args.dataset,
            "collection": args.collection,
            "top_k": args.k,
        },
        "metrics": {
            "total_queries": summary.total_queries,
            "hit_rate": summary.hit_rate,
            "mean_recall_at_5": summary.mean_recall_at_5,
            "mean_recall_at_10": summary.mean_recall_at_10,
            "mean_mrr": summary.mean_mrr,
            "mean_ndcg_at_10": summary.mean_ndcg_at_10,
            "p50_latency_ms": summary.p50_latency_ms,
            "p95_latency_ms": summary.p95_latency_ms,
        },
        "failures": [
            {"id": f.query_id, "query": f.query, "expected": f.expected_files, "retrieved": f.retrieved_files}
            for f in summary.failures
        ],
    }

    with open(output_file, "w") as f:
        json.dump(data, f, indent=2)

    print(f"  📄 Results saved to: {output_file}")
    return output_file


async def main():
    parser = argparse.ArgumentParser(description="Run DevMind retrieval evaluation")
    parser.add_argument(
        "--dataset",
        default="evaluation/golden_dataset/dataset.jsonl",
        help="Path to golden dataset",
    )
    parser.add_argument("--label", default="default", help="Label for this run")
    parser.add_argument("--collection", default=None, help="Qdrant collection name")
    parser.add_argument("--k", type=int, default=10, help="Top-k results to evaluate")
    parser.add_argument("--no-save", action="store_true", help="Don't save results to file")
    args = parser.parse_args()

    # Import search client (adjust this import based on actual structure)
    try:
        from devmind.api.routes_search import RetrievalPipeline
        from devmind.core.database import get_db
        
        # Initialize client
        db = next(get_db())
        pipeline = RetrievalPipeline()
        
        # Create a simple wrapper to match evaluator interface
        class SearchClient:
            async def search(self, query: str, top_k: int = 10, collection: str = None):
                results = await pipeline.search(query=query, top_k=top_k)
                return results
        
        client = SearchClient()
    except Exception as e:
        print(f"Error initializing search client: {e}")
        print("Make sure DevMind backend is running and accessible")
        sys.exit(1)

    evaluator = RetrievalEvaluator(client, args.dataset)

    print(f"\n🔍 Running evaluation on {args.dataset}")
    print(f"📊 Collection: {args.collection or 'default'}")
    print(f"🎯 Top-k: {args.k}\n")

    summary = await evaluator.evaluate(k=args.k, collection=args.collection)

    print_summary(summary, args.label)
    
    if not args.no_save:
        save_results(summary, args.label, args)


if __name__ == "__main__":
    asyncio.run(main())
