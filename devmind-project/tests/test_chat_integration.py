"""
Integration Tests for Chat Engine.

Tests the complete chat workflow including:
- RAG retrieval
- LLM generation
- Context management
- Streaming
"""

import pytest
from pathlib import Path
from devmind.llm import ChatEngine
from devmind.retrieval import RetrievalPipeline, RetrievalConfig
from devmind.embeddings import Encoder, ModelManager
from devmind.vectorstore import IndexManager
from devmind.chunking import Chunk


@pytest.mark.integration
class TestChatEngineIntegration:
    """Integration tests for ChatEngine."""
    
    @pytest.fixture
    def chat_engine(self, tmp_path):
        """Create a test chat engine with mocked components."""
        # Setup retrieval pipeline
        model_manager = ModelManager(device="cpu")
        encoder = Encoder(model_type="mvp", model_manager=model_manager)
        index_manager = IndexManager(base_path=tmp_path, dimension=384)
        
        config = RetrievalConfig(top_k=3)
        retrieval_pipeline = RetrievalPipeline(
            index_manager=index_manager,
            encoder=encoder,
            config=config
        )
        
        # Add test data
        test_chunks = [
            Chunk(
                content="def calculate_sum(a, b):\n    return a + b",
                metadata={"file": "math.py", "type": "function", "name": "calculate_sum"}
            ),
            Chunk(
                content="class Calculator:\n    def __init__(self):\n        self.result = 0",
                metadata={"file": "calculator.py", "type": "class"}
            ),
            Chunk(
                content="# Main entry point\nif __name__ == '__main__':\n    app.run()",
                metadata={"file": "main.py", "type": "script"}
            )
        ]
        
        index_manager.create_index("test_codebase")
        index_manager.add_chunks("test_codebase", test_chunks, encoder)
        
        # Create chat engine (will need LLM manager)
        from devmind.llm import get_llm_manager
        
        try:
            llm_manager = get_llm_manager()
            engine = ChatEngine(
                retrieval_pipeline=retrieval_pipeline,
                llm_manager=llm_manager,
                max_context_tokens=4000
            )
            return engine
        except Exception as e:
            pytest.skip(f"LLM manager not available: {e}")
    
    @pytest.mark.asyncio
    async def test_basic_chat_workflow(self, chat_engine):
        """Test basic chat question and answer."""
        response = await chat_engine.chat(
            index_name="test_codebase",
            query="How do I calculate sum of two numbers?"
        )
        
        assert isinstance(response, dict)
        assert "answer" in response
        assert "sources" in response
        assert len(response["answer"]) > 0
    
    @pytest.mark.asyncio
    async def test_chat_with_empty_index(self, chat_engine):
        """Test chat with empty/non-existent index."""
        # Should handle gracefully
        with pytest.raises(Exception):
            await chat_engine.chat(
                index_name="nonexistent",
                query="test query"
            )
    
    @pytest.mark.asyncio
    async def test_streaming_response(self, chat_engine):
        """Test streaming chat response."""
        chunks_received = []
        
        async for chunk in chat_engine.stream(
            index_name="test_codebase",
            query="Explain the Calculator class"
        ):
            chunks_received.append(chunk)
        
        # Should receive multiple chunks
        assert len(chunks_received) > 0
        
        # Reconstruct full response
        full_response = "".join(chunks_received)
        assert len(full_response) > 0
    
    @pytest.mark.asyncio
    async def test_context_truncation(self, chat_engine):
        """Test that context is truncated to max_context_tokens."""
        # Create a very long query
        long_query = "Explain " + " ".join(["the code"] * 1000)
        
        # Should truncate gracefully
        response = await chat_engine.chat(
            index_name="test_codebase",
            query=long_query
        )
        
        assert isinstance(response, dict)
        # Should still get a response despite truncation
        assert len(response.get("answer", "")) > 0
    
    @pytest.mark.asyncio
    async def test_source_citation(self, chat_engine):
        """Test that sources are properly cited."""
        response = await chat_engine.chat(
            index_name="test_codebase",
            query="What functions are available?"
        )
        
        assert "sources" in response
        sources = response["sources"]
        
        # Should have source information
        if len(sources) > 0:
            assert "file" in sources[0] or "content" in sources[0]
    
    @pytest.mark.asyncio
    async def test_follow_up_conversation(self, chat_engine):
        """Test multi-turn conversation with context."""
        # First question
        response1 = await chat_engine.chat(
            index_name="test_codebase",
            query="What is the Calculator class?",
            conversation_id="test_conv_1"
        )
        
        assert len(response1.get("answer", "")) > 0
        
        # Follow-up question (assuming conversation support)
        response2 = await chat_engine.chat(
            index_name="test_codebase",
            query="How do I use it?",
            conversation_id="test_conv_1"
        )
        
        assert len(response2.get("answer", "")) > 0


@pytest.mark.integration
class TestEndToEndWorkflow:
    """End-to-end integration tests."""
    
    @pytest.mark.asyncio
    async def test_complete_rag_pipeline(self, tmp_path):
        """Test complete pipeline: ingestion → retrieval → chat."""
        from devmind.ingestion import IngestionPipeline, PipelineConfig, FileType
        
        # 1. Create test code files
        test_dir = tmp_path / "test_project"
        test_dir.mkdir()
        
        (test_dir / "utils.py").write_text("""
def add(a, b):
    '''Add two numbers.'''
    return a + b

def multiply(a, b):
    '''Multiply two numbers.'''
    return a * b
""")
        
        # 2. Run ingestion
        config = PipelineConfig(
            source_path=test_dir,
            file_types=[FileType.CODE],
            languages=["python"]
        )
        
        pipeline = IngestionPipeline(config)
        result = pipeline.run()
        
        assert result.total_chunks_generated > 0
        
        # 3. Add to index
        model_manager = ModelManager(device="cpu")
        encoder = Encoder(model_type="mvp", model_manager=model_manager)
        index_manager = IndexManager(base_path=tmp_path / "indices", dimension=384)
        
        index_manager.create_index("test_e2e")
        index_manager.add_chunks("test_e2e", result.chunks, encoder)
        
        # 4. Search
        retrieval_config = RetrievalConfig(top_k=2)
        retrieval_pipeline = RetrievalPipeline(
            index_manager=index_manager,
            encoder=encoder,
            config=retrieval_config
        )
        
        search_results = retrieval_pipeline.search("test_e2e", query="add numbers")
        
        assert len(search_results) > 0
        assert any("add" in r.content.lower() for r in search_results)
    
    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self, tmp_path):
        """Test that system recovers from errors gracefully."""
        from devmind.ingestion import IngestionPipeline, PipelineConfig
        
        # Create a directory with some valid and some invalid files
        test_dir = tmp_path / "mixed_project"
        test_dir.mkdir()
        
        # Valid file
        (test_dir / "valid.py").write_text("def test(): pass")
        
        # Invalid/corrupted file
        (test_dir / "corrupted.py").write_bytes(b"\x00\x01\x02\x03\x04")
        
        config = PipelineConfig(source_path=test_dir)
        pipeline = IngestionPipeline(config)
        
        # Should process valid files and skip/log errors for invalid ones
        result = pipeline.run()
        
        # Should have some successful chunks
        assert result.total_files_scanned >= 2
        # Should have processed at least the valid file
        assert result.total_files_processed >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
