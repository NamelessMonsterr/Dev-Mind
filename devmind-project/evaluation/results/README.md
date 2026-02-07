# Evaluation Results

This directory stores evaluation run results as JSON files.

## File Format

Each run produces a timestamped JSON file:

```
eval_{label}_{timestamp}.json
```

Example: `eval_baseline_20260207_154530.json`

## Structure

```json
{
  "run_label": "baseline",
  "timestamp": "2026-02-07T15:45:30",
  "config": {
    "dataset": "evaluation/golden_dataset/dataset.jsonl",
    "collection": null,
    "top_k": 10
  },
  "metrics": {
    "total_queries": 120,
    "hit_rate": 0.725,
    "mean_recall_at_5": 0.681,
    "mean_recall_at_10": 0.781,
    "mean_mrr": 0.634,
    "mean_ndcg_at_10": 0.712,
    "p50_latency_ms": 125,
    "p95_latency_ms": 340
  },
  "failures": [{ "id": "q_042", "query": "How does caching work?" }]
}
```

## Usage

```bash
# Compare two runs
python -m evaluation.scripts.compare_runs \
  evaluation/results/eval_baseline_20260207.json \
  evaluation/results/eval_new_model_20260207.json
```

## Git

This directory is tracked in git, but large result files (>1MB) should be in `.gitignore`.
