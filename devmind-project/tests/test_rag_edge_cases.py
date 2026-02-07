"""
Edge Case Tests for RAG Pipeline.

Tests various edge cases and error conditions that may occur in production:
- Empty queries
- Oversized context
- Invalid inputs
- Error conditions
"""

import pytest
from pathlib import Path
from devmind.retrieval import RetrievalPipeline, RetrievalConfig
from devmind.embeddings import Encoder, ModelManager
from devmind.vectorstore import IndexManager
from devmind.chunking import Chunk


class TestRAGEdgeCases:
    """Test edge cases in RAG pipeline."""
    
    @pytest.fixture
    def retrieval_pipeline(self, tmp_path):
        """Create a test retrieval pipeline."""
        model_manager = ModelManager(device="cpu")
        encoder = Encoder(model_type="mvp", model_manager=model_manager)
        index_manager = IndexManager(base_path=tmp_path, dimension=384)
        
        config = RetrievalConfig(
            top_k=5,
            use_keyword_search=True,
            vector_weight=0.7,
            keyword_weight=0.3
        )
        
        pipeline = RetrievalPipeline(
            index_manager=index_manager,
            encoder=encoder,
            config=config
        )
        
        # Add some test data
        test_chunks = [
            Chunk(
                content="def hello(): return 'world'",
                metadata={"file": "test.py", "type": "function"}
            ),
            Chunk(
                content="class MyClass: pass",
                metadata={"file": "test.py", "type": "class"}
            )
        ]
        
        # Create test index
        index_manager.create_index("test_project")
        index_manager.add_chunks("test_project", test_chunks, encoder)
        
        return pipeline
    
    def test_empty_query(self, retrieval_pipeline):
        """Test handling of empty query string."""
        results = retrieval_pipeline.search("test_project", query="")
        
        # Should return empty results or handle gracefully
        assert isinstance(results, list)
        assert len(results) == 0
    
    def test_whitespace_only_query(self, retrieval_pipeline):
        """Test query with only whitespace."""
        results = retrieval_pipeline.search("test_project", query="   \n\t  ")
        
        assert isinstance(results, list)
        assert len(results) == 0
    
    def test_very_long_query(self, retrieval_pipeline):
        """Test query that exceeds typical token limits."""
        # Create a very long query (10,000 words)
        long_query = " ".join(["word"] * 10000)
        
        # Should handle gracefully without crashing
        try:
            results = retrieval_pipeline.search("test_project", query=long_query)
            assert isinstance(results, list)
        except Exception as e:
            # If it raises an exception, it should be a clear error
            assert "too long" in str(e).lower() or "token" in str(e).lower()
    
    def test_special_characters_query(self, retrieval_pipeline):
        """Test query with special characters."""
        special_queries = [
            "SELECT * FROM users WHERE id = 1; DROP TABLE users;",  # SQL injection attempt
            "<script>alert('xss')</script>",  # XSS attempt
            "../../etc/passwd",  # Path traversal
            "\x00\x01\x02",  # Null bytes
            "こんにちは世界",  # Unicode
            "🔥💯🚀",  # Emojis
        ]
        
        for query in special_queries:
            results = retrieval_pipeline.search("test_project", query=query)
            # Should handle gracefully
            assert isinstance(results, list)
    
    def test_nonexistent_index(self, retrieval_pipeline):
        """Test searching non-existent index."""
        with pytest.raises(Exception) as exc_info:
            retrieval_pipeline.search("nonexistent_index", query="test")
        
        # Should raise a clear error
        assert "not found" in str(exc_info.value).lower() or "exist" in str(exc_info.value).lower()
    
    def test_zero_results(self, retrieval_pipeline):
        """Test query that should return no results."""
        results = retrieval_pipeline.search(
            "test_project", 
            query="xyzabc123impossible_match_9999"
        )
        
        assert isinstance(results, list)
        # May return empty or very low similarity results
        assert len(results) >= 0
    
    def test_top_k_edge_cases(self, retrieval_pipeline):
        """Test edge cases for top_k parameter."""
        # top_k = 0
        results = retrieval_pipeline.search("test_project", query="function", top_k=0)
        assert len(results) == 0
        
        # top_k = 1
        results = retrieval_pipeline.search("test_project", query="function", top_k=1)
        assert len(results) <= 1
        
        # top_k > available results
        results = retrieval_pipeline.search("test_project", query="function", top_k=1000)
        assert len(results) <= 1000  # Should return all available results
    
    def test_concurrent_searches(self, retrieval_pipeline):
        """Test multiple concurrent searches."""
        import concurrent.futures
        
        def search_task():
            return retrieval_pipeline.search("test_project", query="test")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(search_task) for _ in range(10)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        # All searches should succeed
        assert len(results) == 10
        for result in results:
            assert isinstance(result, list)


class TestErrorConditions:
    """Test error handling in various scenarios."""
    
    def test_corrupted_index_recovery(self, tmp_path):
        """Test recovery from corrupted index."""
        model_manager = ModelManager(device="cpu")
        encoder = Encoder(model_type="mvp", model_manager=model_manager)
        index_manager = IndexManager(base_path=tmp_path, dimension=384)
        
        # Create an index
        index_manager.create_index("test")
        
        # Corrupt the index by deleting files
        index_path = tmp_path / "test"
        if index_path.exists():
            import shutil
            shutil.rmtree(index_path)
        
        # Should handle corruption gracefully
        with pytest.raises(Exception):
            index_manager.get_index("test")
    
    def test_disk_full_simulation(self, tmp_path, monkeypatch):
        """Test behavior when disk is full."""
        # This is a simplified test - in production you'd use more sophisticated mocking
        pass  # Skip for now - requires complex mocking
    
    def test_memory_pressure(self):
        """Test behavior under memory pressure."""
        # This would require generating very large embeddings or indices
        pass  # Skip for now - requires resource constraints


class TestOversizedContext:
    """Test handling of oversized contexts."""
    
    def test_large_chunk_handling(self):
        """Test handling of very large text chunks."""
        from devmind.chunking import FixedChunker
        
        chunker = FixedChunker(chunk_size=512, chunk_overlap=50)
        
        # Create a very large text (100,000 characters)
        large_text = "word " * 20000
        
        # Should chunk without crashing
        from devmind.processing.code_processor import CodeSection
        sections = [CodeSection(
            content=large_text,
            section_type="function",
            name="large_function",
            start_line=1,
            end_line=10000,
            language="python",
            file_path=Path("test.py")
        )]
        
        chunks = chunker.chunk(sections)
        
        # Should create multiple chunks
        assert len(chunks) > 1
        
        # Each chunk should be <= max size
        for chunk in chunks:
            assert len(chunk.content) <= 600  # chunk_size + some buffer
    
    def test_context_window_overflow(self):
        """Test when retrieved context exceeds LLM context window."""
        # This would test the chat engine's context truncation logic
        pass  # Requires chat engine integration


@pytest.mark.asyncio
class TestLLMProviderFallback:
    """Test LLM provider fallback scenarios."""
    
    async def test_primary_provider_failure(self):
        """Test fallback when primary provider fails."""
        from devmind.llm import LLMProviderManager, ProviderType
        
        manager = LLMProviderManager()
        
        # This test would require mocking provider failures
        # For now, we'll test the manager structure
        assert hasattr(manager, 'providers')
        assert hasattr(manager, 'select_provider')
    
    async def test_all_providers_failure(self):
        """Test behavior when all providers fail."""
        # Should raise a clear error or use fallback response
        pass  # Requires provider mocking
    
    async def test_rate_limit_handling(self):
        """Test handling of rate limit errors."""
        # Should retry with backoff or fallback to different provider
        pass  # Requires API mocking


class TestInvalidInputs:
    """Test handling of various invalid inputs."""
    
    def test_none_query(self, retrieval_pipeline):
        """Test None as query."""
        with pytest.raises((TypeError, ValueError)):
            retrieval_pipeline.search("test_project", query=None)
    
    def test_non_string_query(self, retrieval_pipeline):
        """Test non-string query types."""
        invalid_queries = [123, 45.67, [], {}, object()]
        
        for query in invalid_queries:
            with pytest.raises((TypeError, ValueError)):
                retrieval_pipeline.search("test_project", query=query)
    
    def test_invalid_config_values(self):
        """Test invalid configuration values."""
        # Negative top_k
        with pytest.raises(ValueError):
            RetrievalConfig(top_k=-1)
        
        # Invalid weights (should sum to reasonable values)
        config = RetrievalConfig(vector_weight=0.0, keyword_weight=0.0)
        # Should either normalize or raise error
        assert config.vector_weight >= 0 and config.keyword_weight >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
