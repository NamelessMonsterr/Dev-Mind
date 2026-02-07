"""
Unit tests for DevMind Embedding Service.
"""

import pytest
import numpy as np
from devmind.embeddings.model_manager import ModelManager, get_model_manager
from devmind.embeddings.encoder import Encoder
from devmind.embeddings.batch_processor import BatchProcessor


class TestModelManager:
    """Tests for ModelManager."""
    
    def test_init(self):
        """Test ModelManager initialization."""
        manager = ModelManager(device="cpu")
        assert manager.get_device() == "cpu"
        assert len(manager.get_loaded_models()) == 0
    
    def test_load_model(self):
        """Test loading a model."""
        manager = ModelManager(device="cpu")
        model = manager.get_model("mvp")
        
        assert model is not None
        assert "all-MiniLM-L6-v2" in manager.get_loaded_models()[0]
    
    def test_model_caching(self):
        """Test that models are cached."""
        manager = ModelManager(device="cpu")
        
        model1 = manager.get_model("mvp")
        model2 = manager.get_model("mvp")
        
        assert model1 is model2  # Same object
        assert len(manager.get_loaded_models()) == 1
    
    def test_invalid_model_type(self):
        """Test that invalid model type raises error."""
        manager = ModelManager(device="cpu")
        
        with pytest.raises(ValueError, match="Unknown model type"):
            manager.get_model("invalid_model")
    
    def test_singleton(self):
        """Test that get_model_manager returns singleton."""
        manager1 = get_model_manager()
        manager2 = get_model_manager()
        
        assert manager1 is manager2


class TestEncoder:
    """Tests for Encoder."""
    
    @pytest.fixture
    def encoder(self):
        """Create an encoder for testing."""
        return Encoder(model_type="mvp")
    
    def test_encode_single(self, encoder):
        """Test encoding a single text."""
        vector = encoder.encode("Hello, world!")
        
        assert isinstance(vector, np.ndarray)
        assert vector.shape == (384,)  # MiniLM dimension
        assert vector.dtype == np.float32
    
    def test_encode_empty_text(self, encoder):
        """Test encoding empty text returns zero vector."""
        vector = encoder.encode("")
        
        assert isinstance(vector, np.ndarray)
        assert vector.shape == (384,)
        assert np.all(vector == 0)
    
    def test_encode_batch(self, encoder):
        """Test encoding multiple texts."""
        texts = ["First text", "Second text", "Third text"]
        vectors = encoder.encode_batch(texts)
        
        assert isinstance(vectors, np.ndarray)
        assert vectors.shape == (3, 384)
        assert vectors.dtype == np.float32
    
    def test_encode_batch_empty_list(self, encoder):
        """Test encoding empty list."""
        vectors = encoder.encode_batch([])
        
        assert vectors.shape == (0, 384)
    
    def test_encode_batch_with_empty_texts(self, encoder):
        """Test batch encoding with some empty texts."""
        texts = ["Valid text", "", "Another text"]
        vectors = encoder.encode_batch(texts)
        
        assert vectors.shape == (3, 384)
        # Second vector should be zeros
        assert np.all(vectors[1] == 0)
    
    def test_get_embedding_dim(self, encoder):
        """Test getting embedding dimension."""
        dim = encoder.get_embedding_dim()
        assert dim == 384
    
    def test_get_model_info(self, encoder):
        """Test getting model information."""
        info = encoder.get_model_info()
        
        assert info["model_type"] == "mvp"
        assert info["embedding_dim"] == 384
        assert "device" in info


class TestBatchProcessor:
    """Tests for BatchProcessor."""
    
    @pytest.fixture
    def encoder(self):
        return Encoder(model_type="mvp")
    
    @pytest.fixture
    def processor(self, encoder):
        return BatchProcessor(encoder, batch_size=2)
    
    def test_process_batches(self, processor):
        """Test processing batches."""
        texts = ["Text 1", "Text 2", "Text 3", "Text 4"]
        metadatas = [{"id": i} for i in range(4)]
        
        batches = list(processor.process_batches(texts, metadatas, show_progress=False))
        
        assert len(batches) == 2  # 4 texts / batch_size 2
        
        # Check first batch
        embeddings1, meta1 = batches[0]
        assert embeddings1.shape == (2, 384)
        assert len(meta1) == 2
        assert meta1[0]["id"] == 0
    
    def test_process_all(self, processor):
        """Test processing all texts at once."""
        texts = ["Text 1", "Text 2", "Text 3"]
        metadatas = [{"id": i} for i in range(3)]
        
        all_embeddings, all_meta = processor.process_all(
            texts, metadatas, show_progress=False
        )
        
        assert all_embeddings.shape == (3, 384)
        assert len(all_meta) == 3
    
    def test_mismatched_metadata(self, processor):
        """Test that mismatched metadata raises error."""
        texts = ["Text 1", "Text 2"]
        metadatas = [{"id": 1}]  # Wrong length
        
        with pytest.raises(ValueError, match="must match"):
            list(processor.process_batches(texts, metadatas))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
