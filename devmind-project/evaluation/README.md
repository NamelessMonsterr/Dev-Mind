# DevMind Evaluation Framework

Comprehensive evaluation framework for measuring retrieval quality using a golden dataset.

## Purpose

Before making changes to the embedding model, chunking strategy, or retrieval pipeline, you need **quantitative evidence** that the change actually improves quality. This framework provides that evidence through standardized metrics.

## Quick Start

```bash
# 1. Run baseline evaluation
python -m evaluation.scripts.run_eval --label baseline

# 2. Make a change (swap embedding model, adjust chunking, etc.)

# 3. Run evaluation again
python -m evaluation.scripts.run_eval --label new_model --collection bge_large_v1

# 4. Compare results
python -m evaluation.scripts.compare_runs \
  evaluation/results/eval_baseline_*.json \
  evaluation/results/eval_new_model_*.json
```

## Components

### 1. Golden Dataset (`golden_dataset/`)

A curated set of 100-150 queries with expected results. Each query specifies:

- The natural language question
- Which code chunks should be retrieved
- Relevance level (primary vs secondary)
- Expected keywords in LLM response

See [`golden_dataset/README.md`](golden_dataset/README.md) for annotation guidelines.

### 2. Metrics (`metrics/`)

Four core metrics:

- **Recall@K**: What % of expected results appear in top-k?
- **MRR (Mean Reciprocal Rank)**: Rank of first relevant result
- **NDCG@K**: Ranking quality (accounts for position)
- **Answer Relevance**: Keyword coverage in LLM responses

### 3. Evaluator (`metrics/evaluator.py`)

Runs queries through your retrieval pipeline, collects results, computes metrics.

### 4. CLI Tools (`scripts/`)

- `run_eval.py`: Execute evaluation
- `compare_runs.py`: A/B comparison

## Metrics Target

| Metric               | Target | Current            |
| -------------------- | ------ | ------------------ |
| **Recall@10**        | ≥ 80%  | TBD (run baseline) |
| **Hit Rate (top 5)** | ≥ 75%  | TBD                |
| **MRR**              | ≥ 0.70 | TBD                |
| **NDCG@10**          | ≥ 0.75 | TBD                |

## Workflow

### Initial Baseline

```bash
# Create golden dataset (2-4 hours of manual work)
# Edit evaluation/golden_dataset/dataset.jsonl

# Run baseline with current model (MiniLM)
python -m evaluation.scripts.run_eval --label miniLM_baseline

# Output:
# ============================================================
#   EVALUATION REPORT: miniLM_baseline
#   Queries Evaluated:  120
#   Hit Rate (top 5):   72.5%
#   Mean Recall@10:     0.781
#   Recall@10 vs Target (≥80%): ❌ FAIL
# ============================================================
```

### Evaluating a Change

```bash
# Example: Testing BGE-Large embedding model

# 1. Deploy new model, reindex with new collection name
docker-compose exec backend python -m scripts.reindex_with_model \
  --model bge-large-en --collection bge_large_v1

# 2. Run eval against new collection
python -m evaluation.scripts.run_eval \
  --label bge_large \
  --collection bge_large_v1

# 3. Compare
python -m evaluation.scripts.compare_runs \
  evaluation/results/eval_miniLM_baseline_*.json \
  evaluation/results/eval_bge_large_*.json

# Output:
#   Metric               Baseline  Candidate      Delta
#   Hit Rate                0.725      0.841     +0.116 ✅
#   Recall@10               0.781      0.862     +0.081 ✅
#   Latency P95              180ms      340ms     +160ms 🔴
#
#   IMPROVEMENTS: Hit Rate, Recall@10
#   REGRESSIONS DETECTED: Latency P95
#   Review regressions before deploying
```

Now you have **hard evidence** that BGE-Large improves recall by 8.1% but adds 160ms latency. You can make an informed tradeoff decision.

## Integration with CI/CD

```yaml
# .github/workflows/eval.yml
name: Retrieval Quality Check

on: [pull_request]

jobs:
  eval:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run evaluation
        run: |
          python -m evaluation.scripts.run_eval --label pr_${{ github.event.pull_request.number }}

      - name: Compare with main
        run: |
          # Download baseline from main branch
          python -m evaluation.scripts.compare_runs \
            baseline_main.json \
            evaluation/results/eval_pr_*.json

      - name: Fail on regression
        run: |
          # Parse comparison, exit 1 if Recall@10 decreased > 5%
```

## Maintenance

- **Weekly**: Add 5-10 queries from user feedback
- **Monthly**: Re-validate expected chunks (code changes may invalidate them)
- **After big changes**: Re-run full baseline

## Architecture

```
evaluation/
├── golden_dataset/
│   ├── README.md           # Annotation guidelines
│   └── dataset.jsonl       # 100-150 query-result pairs
├── metrics/
│   ├── metrics.py          # Recall@K, MRR, NDCG
│   ├── evaluator.py        # Evaluation engine
│   └── __init__.py
├── scripts/
│   ├── run_eval.py         # CLI: run evaluation
│   ├── compare_runs.py     # CLI: A/B comparison
│   └── __init__.py
├── results/
│   └── .gitkeep            # Timestamped JSON results
└── README.md               # This file
```

## Example Output

### run_eval.py

```
============================================================
  EVALUATION REPORT: baseline
  2026-02-07T22:30:15
============================================================

  Queries Evaluated:  120
  Hit Rate (top 5):   72.5%
  Mean Recall@5:      0.681
  Mean Recall@10:     0.781
  Mean MRR:           0.634
  Mean NDCG@10:       0.712
  Latency P50:        125ms
  Latency P95:        340ms

  Recall@10 vs Target (≥80%): ❌ FAIL

  ⚠️  Failed Queries (8):
    • [q_042] "How does caching work?"
      Expected: ['cache/redis_client.py', 'cache/manager.py']
      Got:      ['config.py', 'utils.py', 'logger.py']

============================================================

  📄 Results saved to: evaluation/results/eval_baseline_20260207_223015.json
```

### compare_runs.py

```
=================================================================
  A/B COMPARISON
  Baseline:  miniLM_baseline (2026-02-07)
  Candidate: bge_large (2026-02-07)
=================================================================

  Metric               Baseline  Candidate      Delta
  -------------------------------------------------------
  Hit Rate                0.725      0.841     +0.116 ✅
  Recall@5                0.681      0.779     +0.098 ✅
  Recall@10               0.781      0.862     +0.081 ✅
  MRR                     0.634      0.711     +0.077 ✅
  NDCG@10                 0.712      0.798     +0.086 ✅
  Latency P50              125ms      180ms      +55ms 🔴
  Latency P95              340ms      500ms     +160ms 🔴

=================================================================

  ✅ IMPROVEMENTS: Hit Rate, Recall@5, Recall@10, MRR, NDCG@10
  ⚠️  REGRESSIONS DETECTED: Latency P50, Latency P95
  ⚡ Review regressions before deploying

=================================================================
```

## Next Steps

1. **Build golden dataset** (2-4 hours): Capture 100-150 real developer queries
2. **Run baseline**: Establish current system metrics
3. **Set targets**: Decide if current metrics meet production bar
4. **Iterate**: Use eval framework to guide model/chunking improvements

The evaluation framework is your **force multiplier** for quality improvements.
