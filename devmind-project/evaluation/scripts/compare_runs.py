"""
A/B comparison tool for evaluation results.

Compares two evaluation runs to detect improvements or regressions.

Usage:
    python -m evaluation.scripts.compare_runs baseline.json candidate.json
"""

import json
import sys
from pathlib import Path


def compare(baseline_path: str, candidate_path: str) -> None:
    """Compare two evaluation runs and print diff."""
    with open(baseline_path) as f:
        baseline = json.load(f)
    with open(candidate_path) as f:
        candidate = json.load(f)

    b = baseline["metrics"]
    c = candidate["metrics"]

    print(f"\n{'=' * 65}")
    print(f"  A/B COMPARISON")
    print(f"  Baseline:  {baseline['run_label']} ({baseline['timestamp'][:10]})")
    print(f"  Candidate: {candidate['run_label']} ({candidate['timestamp'][:10]})")
    print(f"{'=' * 65}\n")
    print(f"  {'Metric':<20} {'Baseline':>10} {'Candidate':>10} {'Delta':>10}")
    print(f"  {'-' * 55}")

    metrics = [
        ("Hit Rate", "hit_rate", True),
        ("Recall@5", "mean_recall_at_5", True),
        ("Recall@10", "mean_recall_at_10", True),
        ("MRR", "mean_mrr", True),
        ("NDCG@10", "mean_ndcg_at_10", True),
        ("Latency P50", "p50_latency_ms", False),  # Lower is better
        ("Latency P95", "p95_latency_ms", False),
    ]

    regressions = []
    improvements = []
    
    for name, key, higher_is_better in metrics:
        bv = b[key]
        cv = c[key]
        delta = cv - bv
        direction = "+" if delta > 0 else ""

        if key.endswith("_ms"):
            fmt = lambda v: f"{v:.0f}ms"
            delta_str = f"{direction}{delta:.0f}ms"
        else:
            fmt = lambda v: f"{v:.3f}"
            delta_str = f"{direction}{delta:.3f}"

        is_better = (delta > 0) == higher_is_better
        is_worse = (delta < 0) == higher_is_better and abs(delta) > 0.01
        is_improvement = is_better and abs(delta) > 0.01
        
        indicator = "✅" if is_improvement else ("🔴" if is_worse else "➖")

        print(f"  {name:<20} {fmt(bv):>10} {fmt(cv):>10} {delta_str:>10} {indicator}")

        if is_worse:
            regressions.append(name)
        if is_improvement:
            improvements.append(name)

    print(f"\n{'=' * 65}")
    
    if regressions:
        print(f"\n  ⚠️  REGRESSIONS DETECTED: {', '.join(regressions)}")
    
    if improvements:
        print(f"\n  ✅ IMPROVEMENTS: {', '.join(improvements)}")
    
    if not regressions and not improvements:
        print(f"\n  ➖ No significant changes detected")
    
    if not regressions:
        print(f"\n  🎯 Safe to proceed with deployment")
    else:
        print(f"\n  ⚡ Review regressions before deploying")

    print(f"\n{'=' * 65}\n")
    
    # Show new failures if any
    baseline_failures = {f["id"] for f in baseline.get("failures", [])}
    candidate_failures = {f["id"] for f in candidate.get("failures", [])}
    
    new_failures = candidate_failures - baseline_failures
    fixed_failures = baseline_failures - candidate_failures
    
    if new_failures:
        print(f"  ⚠️  New failures ({len(new_failures)}):")
        for f in candidate.get("failures", []):
            if f["id"] in new_failures:
                print(f"    • [{f['id']}] {f['query']}")
    
    if fixed_failures:
        print(f"  ✅ Fixed failures ({len(fixed_failures)}):")
        for f in baseline.get("failures", []):
            if f["id"] in fixed_failures:
                print(f"    • [{f['id']}] {f['query']}")
    
    print()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python compare_runs.py <baseline.json> <candidate.json>")
        print("\nExample:")
        print("  python -m evaluation.scripts.compare_runs \\")
        print("    evaluation/results/eval_baseline_20260207.json \\")
        print("    evaluation/results/eval_new_model_20260207.json")
        sys.exit(1)
    
    baseline = sys.argv[1]
    candidate = sys.argv[2]
    
    if not Path(baseline).exists():
        print(f"Error: Baseline file not found: {baseline}")
        sys.exit(1)
    
    if not Path(candidate).exists():
        print(f"Error: Candidate file not found: {candidate}")
        sys.exit(1)
    
    compare(baseline, candidate)
