"""
Demo script for DevMind Embedding Service.
Tests the core functionality end-to-end.
"""

import numpy as np
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Run the demo."""
    logger.info("=" * 60)
    logger.info("DevMind Embedding Service Demo")
    logger.info("=" * 60)
    
    # Import modules
    from devmind.embeddings import Encoder, BatchProcessor
    from devmind.vectorstore import IndexManager
    
    # 1. Initialize encoder
    logger.info("\n1. Initializing Encoder (MiniLM-L6-v2)...")
    encoder = Encoder(model_type="mvp")
    logger.info(f"   Model info: {encoder.get_model_info()}")
    
    # 2. Create sample data
    logger.info("\n2. Creating sample code snippets...")
    code_samples = [
        "def add(a, b):\n    return a + b",
        "def multiply(x, y):\n    return x * y",
        "class Calculator:\n    def compute(self, expr):\n        return eval(expr)",
        "def factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n-1)",
        "import numpy as np\ndef dot_product(a, b):\n    return np.dot(a, b)",
    ]
    
    metadata = [
        {"source": "math_utils.py", "function": "add", "line": 1},
        {"source": "math_utils.py", "function": "multiply", "line": 5},
        {"source": "calculator.py", "function": "Calculator.compute", "line": 1},
        {"source": "recursion.py", "function": "factorial", "line": 1},
        {"source": "numpy_utils.py", "function": "dot_product", "line": 1},
    ]
    
    logger.info(f"   Created {len(code_samples)} code samples")
    
    # 3. Encode in batches
    logger.info("\n3. Encoding code snippets...")
    processor = BatchProcessor(encoder, batch_size=2)
    embeddings, all_meta = processor.process_all(
        code_samples, 
        metadata, 
        show_progress=True
    )
    logger.info(f"   Generated embeddings: {embeddings.shape}")
    
    # 4. Initialize Index Manager
    logger.info("\n4. Initializing Index Manager...")
    indices_path = Path("./demo_indices")
    manager = IndexManager(base_path=indices_path, dimension=384)
    
    # 5. Add to index
    logger.info("\n5. Adding embeddings to 'code' index...")
    manager.add_to_index("code", embeddings, all_meta)
    logger.info(f"   Index stats: {manager.get_stats()}")
    
    # 6. Test Search - Find addition function
    logger.info("\n6. Testing Search: 'function to add two numbers'...")
    query = "function to add two numbers"
    query_embedding = encoder.encode(query)
    results = manager.search("code", query_embedding, k=3)
    
    logger.info("   ── Top 3 Results ──")
    for i, (score, meta) in enumerate(results, 1):
        logger.info(f"   {i}. Score: {score:.4f}")
        logger.info(f"      Function: {meta['function']}")
        logger.info(f"      Source: {meta['source']}:{meta['line']}")
    
    # 7. Test another query - Recursion
    logger.info("\n7. Testing Search: 'recursive function implementation'...")
    query2 = "recursive function implementation"
    query_embedding2 = encoder.encode(query2)
    results2 = manager.search("code", query_embedding2, k=3)
    
    logger.info("   ── Top 3 Results ──")
    for i, (score, meta) in enumerate(results2, 1):
        logger.info(f"   {i}. Score: {score:.4f}")
        logger.info(f"      Function: {meta['function']}")
        logger.info(f"      Source: {meta['source']}:{meta['line']}")
    
    # 8. Save indices
    logger.info("\n8. Saving indices to disk...")
    manager.save_all()
    logger.info(f"   Saved to: {indices_path}")
    
    # 9. Test reload
    logger.info("\n9. Testing reload from disk...")
    manager2 = IndexManager(base_path=indices_path, dimension=384)
    logger.info(f"   Reloaded stats: {manager2.get_stats()}")
    
    # 10. Cross-index search
    logger.info("\n10. Adding docs to 'docs' index...")
    doc_samples = [
        "DevMind is an AI development assistant",
        "RAG combines retrieval and generation",
    ]
    doc_meta = [
        {"source": "readme.md", "section": "Introduction"},
        {"source": "docs.md", "section": "Architecture"},
    ]
    doc_embeddings, doc_all_meta = processor.process_all(
        doc_samples, doc_meta, show_progress=False
    )
    manager.add_to_index("docs", doc_embeddings, doc_all_meta)
    
    # Search across all indices
    logger.info("\n11. Testing cross-index search: 'AI assistant'...")
    query3 = "AI assistant"
    query_embedding3 = encoder.encode(query3)
    all_results = manager.search_all(query_embedding3, k=3)
    
    logger.info("   ── Results from all indices ──")
    for i, (score, meta, index_name) in enumerate(all_results, 1):
        logger.info(f"   {i}. Score: {score:.4f} | Index: {index_name}")
        logger.info(f"      Source: {meta.get('source', 'N/A')}")
    
    logger.info("\n" + "=" * 60)
    logger.info("✅ Demo completed successfully!")
    logger.info("=" * 60)
    
    # Cleanup
    logger.info("\nCleaning up demo indices...")
    import shutil
    if indices_path.exists():
        shutil.rmtree(indices_path)
    logger.info("   Cleaned up temporary files")


if __name__ == "__main__":
    main()
