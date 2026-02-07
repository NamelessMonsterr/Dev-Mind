"""
Unit tests for Keyword Search Engine.
"""

import pytest

from devmind.retrieval.keyword_search import (
    KeywordSearchEngine,
    KeywordSearchResult,
    BM25Index
)


class TestBM25Index:
    """Tests for BM25Index."""
    
    @pytest.fixture
    def index(self):
        """Create BM25Index instance."""
        return BM25Index(k1=1.5, b=0.75)
    
    def test_add_documents(self, index):
        """Test adding documents to index."""
        chunks = [
            ("chunk1", "def authenticate user with password", {"type": "function"}),
            ("chunk2", "class User model for authentication", {"type": "class"}),
            ("chunk3", "password validation function", {"type": "function"}),
        ]
        
        index.add_documents(chunks)
        
        assert index.num_docs == 3
        assert len(index.documents) == 3
        assert "password" in index.inverted_index
    
    def test_tokenization(self, index):
        """Test text tokenization."""
        tokens = index._tokenize("This is a test function for authentication")
        
        # Should remove stopwords and lowercase
        assert "test" in tokens
        assert "function" in tokens
        assert "authentication" in tokens
        assert "is" not in tokens  # stopword
        assert "a" not in tokens  # stopword
    
    def test_search(self, index):
        """Test BM25 search."""
        # TODO: Implement test with real search
        pass
    
    def test_empty_query(self, index):
        """Test search with empty query."""
        # TODO: Implement test
        pass
    
    def test_no_matches(self, index):
        """Test search with no matching documents."""
        # TODO: Implement test
        pass


class TestKeywordSearchEngine:
    """Tests for KeywordSearchEngine."""
    
    @pytest.fixture
    def engine(self):
        """Create KeywordSearchEngine instance."""
        return KeywordSearchEngine()
    
    def test_index_and_search(self, engine):
        """Test indexing and searching."""
        # TODO: Implement test
        pass
    
    def test_score_normalization(self, engine):
        """Test that scores are normalized to [0, 1]."""
        # TODO: Implement test
        pass
    
    def test_get_stats(self, engine):
        """Test getting index statistics."""
        stats = engine.get_stats()
        
        assert "num_documents" in stats
        assert "vocabulary_size" in stats
        assert "parameters" in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
