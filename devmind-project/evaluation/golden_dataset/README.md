# DevMind Golden Dataset

This directory contains the golden dataset for evaluating retrieval quality.

## Dataset Format

Each entry in `dataset.jsonl` represents a query with its expected results:

```jsonl
{
  "id": "q_001",
  "query": "How do we verify JWT tokens?",
  "category": "code",
  "difficulty": "easy",
  "expected_chunks": [
    {
      "file": "auth/jwt.py",
      "function": "verify_token",
      "line_start": 45,
      "line_end": 67,
      "relevance": "primary"
    }
  ],
  "expected_answer_contains": [
    "jwt.decode",
    "token validation"
  ],
  "annotator": "maya",
  "date": "2026-02-10"
}
```

## Fields

- **id**: Unique query identifier (e.g., `q_001`)
- **query**: Natural language query from user
- **category**: `code`, `docs`, or `cross_ref`
- **difficulty**: `easy`, `medium`, `hard`
- **expected_chunks**: List of code chunks that should be retrieved
  - **file**: File path relative to indexed codebase
  - **function**: Function/class name (optional)
  - **line_start**, **line_end**: Line range
  - **relevance**: `primary` (must be in top 5) or `secondary` (should be in top 10)
- **expected_answer_contains**: Keywords that should appear in LLM response
- **annotator**: Who created this query (maya, alex, jordan)
- **date**: Creation date

## Annotation Guidelines

### Query Selection

Choose queries that represent **real developer workflows**:

1. **Code Understanding** (40%): "How does X work?", "What does Y do?"
2. **Code Location** (30%): "Where is the authentication logic?", "Find the billing module"
3. **Debugging** (20%): "Why would Z fail?", "What validates user input?"
4. **Cross-Reference** (10%): "How are payments and subscriptions related?"

### Difficulty Levels

- **Easy**: Single obvious answer, no ambiguity
- **Medium**: Multiple relevant chunks, needs ranking
- **Hard**: Requires cross-file understanding or domain knowledge

### Relevance Marking

- **Primary**: The definitive answer. If this isn't in top 5, retrieval failed.
- **Secondary**: Helpful context but not essential.

## Building the Dataset

### Phase 1: Bootstrap (30 queries)

Start with common queries from your own development:

```bash
# What did you recently search for in your IDE?
# What did you ask ChatGPT about your code?
# What documentation did you need during onboarding?
```

### Phase 2: Persona Coverage (60 queries)

Have each persona contribute 20 queries:

- **Maya** (Senior Engineer): Architecture, integration, edge cases
- **Alex** (New Developer): Onboarding, "how does this work?", API usage
- **Jordan** (Tech Lead): Performance, security, design decisions

### Phase 3: Failure Analysis (30 queries)

Run the evaluator, find queries with Recall@10 < 0.5, and:

- Add similar queries to catch the pattern
- Verify your expected chunks are actually correct

## Usage

```bash
# Run evaluation
python -m evaluation.scripts.run_eval --dataset evaluation/golden_dataset/dataset.jsonl

# Compare before/after model change
python -m evaluation.scripts.compare_runs \
  evaluation/results/eval_baseline.json \
  evaluation/results/eval_new_model.json
```

## Maintenance

- **Weekly**: Add 5-10 new queries from user feedback
- **After major changes**: Re-validate all expected chunks
- **Monthly**: Prune outdated queries (for code that no longer exists)

## Target Metrics

| Metric               | Target | Notes                     |
| -------------------- | ------ | ------------------------- |
| **Recall@10**        | ≥ 80%  | Core success metric       |
| **Hit Rate (top 5)** | ≥ 75%  | Primary result in top 5   |
| **MRR**              | ≥ 0.70 | Relevance ranking quality |
| **NDCG@10**          | ≥ 0.75 | Overall ranking quality   |
