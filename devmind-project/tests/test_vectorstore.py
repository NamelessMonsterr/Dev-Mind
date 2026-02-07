"""
Unit tests for DevMind Vector Store.
"""

import pytest
import numpy as np
from pathlib import Path
import tempfile
import shutil
from devmind.vectorstore.faiss_client import FAISSClient
from devmind.vectorstore.index_manager import IndexManager


class TestFAISSClient:
    """Tests for FAISSClient."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        temp = tempfile.mkdtemp()
        yield Path(temp)
        shutil.rmtree(temp)
    
    def test_init_new_index(self):
        """Test creating a new index."""
        client = FAISSClient(dimension=384)
        assert client.get_size() == 0
        assert client.dimension == 384
    
    def test_add_vectors(self):
        """Test adding vectors to index."""
        client = FAISSClient(dimension=10)
        
        embeddings = np.random.randn(5, 10).astype('float32')
        client.add(embeddings)
        
        assert client.get_size() == 5
    
    def test_search(self):
        """Test searching for similar vectors."""
        client = FAISSClient(dimension=10)
        
        # Add some vectors
        embeddings = np.random.randn(10, 10).astype('float32')
        client.add(embeddings)
        
        # Search with one of the added vectors
        query = embeddings[0]
        distances, indices = client.search(query, k=3)
        
        assert len(distances) == 3
        assert len(indices) == 3
        assert indices[0] == 0  # Should find itself first
    
    def test_save_and_load(self, temp_dir):
        """Test saving and loading index."""
        index_path = temp_dir / "test_index.faiss"
        
        # Create and populate index
        client1 = FAISSClient(dimension=10, index_path=index_path)
        embeddings = np.random.randn(5, 10).astype('float32')
        client1.add(embeddings)
        client1.save()
        
        # Load index
        client2 = FAISSClient(dimension=10, index_path=index_path)
        
        assert client2.get_size() == 5
    
    def test_wrong_dimension(self):
        """Test that wrong dimension raises error."""
        client = FAISSClient(dimension=10)
        
        embeddings = np.random.randn(5, 20).astype('float32')  # Wrong dimension
        
        with pytest.raises(ValueError, match="dimension"):
            client.add(embeddings)
    
    def test_reset(self):
        """Test resetting index."""
        client = FAISSClient(dimension=10)
        
        embeddings = np.random.randn(5, 10).astype('float32')
        client.add(embeddings)
        assert client.get_size() == 5
        
        client.reset()
        assert client.get_size() == 0


class TestIndexManager:
    """Tests for IndexManager."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        temp = tempfile.mkdtemp()
        yield Path(temp)
        shutil.rmtree(temp)
    
    @pytest.fixture
    def manager(self, temp_dir):
        """Create IndexManager for testing."""
        return IndexManager(base_path=temp_dir, dimension=10)
    
    def test_init(self, manager):
        """Test IndexManager initialization."""
        assert "code" in manager.indices
        assert "docs" in manager.indices
        assert "notes" in manager.indices
        
        stats = manager.get_stats()
        assert all(count == 0 for count in stats.values())
    
    def test_add_to_index(self, manager):
        """Test adding vectors to an index."""
        embeddings = np.random.randn(3, 10).astype('float32')
        metadata = [{"id": i, "text": f"Text {i}"} for i in range(3)]
        
        manager.add_to_index("code", embeddings, metadata)
        
        assert manager.get_stats()["code"] == 3
        assert len(manager.metadata["code"]) == 3
    
    def test_search(self, manager):
        """Test searching an index."""
        # Add some data
        embeddings = np.random.randn(5, 10).astype('float32')
        metadata = [{"id": i} for i in range(5)]
        manager.add_to_index("docs", embeddings, metadata)
        
        # Search
        query = embeddings[0]
        results = manager.search("docs", query, k=3)
        
        assert len(results) == 3
        score, meta = results[0]
        assert "id" in meta
    
    def test_search_with_filter(self, manager):
        """Test searching with metadata filter."""
        embeddings = np.random.randn(5, 10).astype('float32')
        metadata = [{"id": i, "category": "A" if i < 3 else "B"} for i in range(5)]
        manager.add_to_index("docs", embeddings, metadata)
        
        # Search with filter
        query = embeddings[0]
        filter_fn = lambda meta: meta["category"] == "A"
        results = manager.search("docs", query, k=5, filter_fn=filter_fn)
        
        # Should only return category A results
        assert all(meta["category"] == "A" for _, meta in results)
    
    def test_search_all(self, manager):
        """Test searching across all indices."""
        # Add data to multiple indices
        for index_name in ["code", "docs"]:
            embeddings = np.random.randn(3, 10).astype('float32')
            metadata = [{"id": i, "index": index_name} for i in range(3)]
            manager.add_to_index(index_name, embeddings, metadata)
        
        # Search all
        query = np.random.randn(10).astype('float32')
        results = manager.search_all(query, k=5)
        
        assert len(results) <= 5
        # Each result should have (score, metadata, index_name)
        assert all(len(r) == 3 for r in results)
    
    def test_save_and_load(self, temp_dir):
        """Test saving and loading indices."""
        # Create and populate manager
        manager1 = IndexManager(base_path=temp_dir, dimension=10)
        embeddings = np.random.randn(3, 10).astype('float32')
        metadata = [{"id": i} for i in range(3)]
        manager1.add_to_index("code", embeddings, metadata)
        manager1.save_all()
        
        # Load into new manager
        manager2 = IndexManager(base_path=temp_dir, dimension=10)
        
        assert manager2.get_stats()["code"] == 3
        assert len(manager2.metadata["code"]) == 3
    
    def test_clear_index(self, manager):
        """Test clearing a single index."""
        embeddings = np.random.randn(3, 10).astype('float32')
        metadata = [{"id": i} for i in range(3)]
        manager.add_to_index("code", embeddings, metadata)
        
        assert manager.get_stats()["code"] == 3
        
        manager.clear_index("code")
        
        assert manager.get_stats()["code"] == 0
        assert len(manager.metadata["code"]) == 0
    
    def test_clear_all(self, manager):
        """Test clearing all indices."""
        # Add data to all indices
        for index_name in ["code", "docs", "notes"]:
            embeddings = np.random.randn(2, 10).astype('float32')
            metadata = [{"id": i} for i in range(2)]
            manager.add_to_index(index_name, embeddings, metadata)
        
        manager.clear_all()
        
        stats = manager.get_stats()
        assert all(count == 0 for count in stats.values())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
