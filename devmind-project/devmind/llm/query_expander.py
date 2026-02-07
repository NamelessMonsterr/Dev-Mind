"""
Query Expander for DevMind.
Rewrites and expands queries for better retrieval.
"""

from typing import List
import re
import logging

logger = logging.getLogger(__name__)


class QueryExpander:
    """
    Query expansion for better retrieval.
    
    Expands queries with:
    - Synonyms
    - Related terms
    - Code-aware expansions
    """
    
    # Code-aware term mappings
    CODE_TERM_EXPANSIONS = {
        "auth": ["authentication", "authorize", "login", "verify", "jwt", "token"],
        "db": ["database", "sql", "query", "schema", "model", "orm"],
        "api": ["endpoint", "route", "handler", "controller", "service"],
        "test": ["unittest", "pytest", "spec", "assertion", "mock"],
        "config": ["configuration", "settings", "environment", "env"],
        "error": ["exception", "error handling", "try catch", "raise"],
        "log": ["logging", "logger", "debug", "info", "error"],
        "cache": ["caching", "redis", "memcache", "cache key"],
        "async": ["asynchronous", "await", "promise", "coroutine", "future"],
        "http": ["request", "response", "get", "post", "put", "delete"],
        "validation": ["validator", "validate", "check", "verify", "sanitize"],
        "serialize": ["serialization", "json", "marshal", "encode", "decode"],
        "middleware": ["interceptor", "filter", "hook", "wrapper"],
        "model": ["schema", "entity", "dto", "domain", "data model"],
        "controller": ["handler", "view", "endpoint", "route"],
        "service": ["business logic", "use case", "interactor"],
        "repository": ["dao", "data access", "query", "database"],
        "factory": ["builder", "creator", "constructor"],
        "singleton": ["single instance", "global"],
        "encrypt": ["encryption", "decrypt", "cipher", "hash", "crypto"],
        "session": ["session management", "cookie", "state"],
    }
    
    def __init__(self):
        """Initialize query expander."""
        logger.info("QueryExpander initialized")
    
    def expand(self, query: str, max_variants: int = 3) -> List[str]:
        """
        Expand query with synonyms and related terms.
        
        Args:
            query: Original query
            max_variants: Maximum number of variants to generate
            
        Returns:
            List of expanded queries
        """
        logger.info(f"Expanding query: '{query}'")
        
        variants = [query]  # Include original
        
        # Lowercase for matching
        query_lower = query.lower()
        
        # Check for code terms
        for term, expansions in self.CODE_TERM_EXPANSIONS.items():
            if term in query_lower:
                # Generate variants with expansions
                for expansion in expansions[:max_variants - 1]:
                    variant = query_lower.replace(term, expansion)
                    variants.append(variant)
                    
                    if len(variants) >= max_variants + 1:
                        break
                
                if len(variants) >= max_variants + 1:
                    break
        
        # Deduplicate
        variants = list(dict.fromkeys(variants))
        
        # Limit to max_variants
        variants = variants[:max_variants + 1]
        
        logger.info(f"Generated {len(variants)} query variants")
        return variants
    
    def expand_with_context(
        self,
        query: str,
        file_types: List[str] = None,
        languages: List[str] = None
    ) -> List[str]:
        """
        Expand query with context awareness.
        
        Args:
            query: Original query
            file_types: Relevant file types
            languages: Relevant languages
            
        Returns:
            Contextually expanded queries
        """
        variants = self.expand(query)
        
        # Add language-specific variants
        if languages:
            for lang in languages[:2]:  # Top 2 languages
                lang_variant = f"{query} in {lang}"
                variants.append(lang_variant)
        
        return variants
    
    def extract_intent(self, query: str) -> str:
        """
        Extract query intent.
        
        Args:
            query: User query
            
        Returns:
            Detected intent: "code", "documentation", "debugging", "explanation"
        """
        query_lower = query.lower()
        
        # Code-related keywords
        if any(word in query_lower for word in ["function", "class", "method", "implement", "code"]):
            return "code"
        
        # Documentation keywords
        if any(word in query_lower for word in ["how", "what", "why", "explain", "describe"]):
            return "explanation"
        
        # Debugging keywords
        if any(word in query_lower for word in ["error", "bug", "fix", "debug", "issue", "problem"]):
            return "debugging"
        
        # Documentation search
        if any(word in query_lower for word in ["documentation", "docs", "readme", "guide"]):
            return "documentation"
        
        return "code"  # Default
    
    def rewrite_for_code_search(self, query: str) -> str:
        """
        Rewrite query optimized for code search.
        
        Args:
            query: Natural language query
            
        Returns:
            Code-optimized query
        """
        # Remove common question words
        query = re.sub(r'\b(how|what|where|when|why|show|find|get|can|i|you)\b', '', query, flags=re.IGNORECASE)
        
        # Remove articles
        query = re.sub(r'\b(a|an|the)\b', '', query, flags=re.IGNORECASE)
        
        # Clean up extra spaces
        query = ' '.join(query.split())
        
        return query.strip()
