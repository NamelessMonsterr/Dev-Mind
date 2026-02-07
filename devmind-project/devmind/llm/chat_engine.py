"""
Chat Engine for DevMind.
Core orchestration of retrieval + LLM for Q&A.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging
import time

from devmind.retrieval import RetrievalPipeline, FilterCriteria
from devmind.llm.provider import LLMProviderManager, ProviderType
from devmind.llm.prompts import build_chat_prompt
from devmind.llm.answer_builder import AnswerBuilder
from devmind.llm.query_expander import QueryExpander

logger = logging.getLogger(__name__)


@dataclass
class ChatResponse:
    """Chat response with answer and metadata."""
    answer: str
    citations: List[Dict[str, Any]]
    retrieval_stats: Dict[str, Any]
    llm_provider: str
    total_time_ms: float
    reasoning_steps: Optional[List[Dict[str, Any]]] = None


class ChatEngine:
    """
    Core chat engine for DevMind.
    
    Orchestrates:
    1. Query expansion
    2. Retrieval
    3. Context assembly
    4. LLM generation
    5. Citation extraction
    """
    
    def __init__(
        self,
        retrieval_pipeline: RetrievalPipeline,
        llm_manager: LLMProviderManager,
        max_context_tokens: int = 8000
    ):
        """
        Initialize chat engine.
        
        Args:
            retrieval_pipeline: Retrieval pipeline
            llm_manager: LLM provider manager
            max_context_tokens: Maximum context tokens
        """
        self.retrieval_pipeline = retrieval_pipeline
        self.llm_manager = llm_manager
        self.answer_builder = AnswerBuilder(max_context_tokens=max_context_tokens)
        self.query_expander = QueryExpander()
        
        logger.info("ChatEngine initialized")
    
    async def chat(
        self,
        query: str,
        top_k: int = 10,
        use_query_expansion: bool = True,
        use_keyword_search: bool = True,
        filter_criteria: Optional[FilterCriteria] = None,
        provider_type: Optional[ProviderType] = None,
        temperature: float = 0.7
    ) -> ChatResponse:
        """
        Process chat query.
        
        Args:
            query: User query
            top_k: Number of results to retrieve
            use_query_expansion: Whether to expand query
            use_keyword_search: Use hybrid search
            filter_criteria: Optional filters
            provider_type: Force specific LLM provider
            temperature: LLM temperature
            
        Returns:
            ChatResponse with answer and metadata
        """
        start_time = time.time()
        logger.info(f"Chat query: '{query}'")
        
        # Step 1: Query expansion (optional)
        search_query = query
        if use_query_expansion:
            expanded = self.query_expander.expand(query, max_variants=2)
            if len(expanded) > 1:
                search_query = expanded[1]  # Use first expansion
                logger.info(f"Expanded query: '{search_query}'")
        
        # Step 2: Retrieval
        retrieval_start = time.time()
        results = self.retrieval_pipeline.search(
            query=search_query,
            top_k=top_k,
            use_keyword=use_keyword_search,
            filter_criteria=filter_criteria
        )
        retrieval_time = (time.time() - retrieval_start) * 1000
        
        logger.info(f"Retrieved {len(results)} results in {retrieval_time:.2f}ms")
        
        if not results:
            return ChatResponse(
                answer="I couldn't find any relevant information in the codebase to answer your question.",
                citations=[],
                retrieval_stats={
                    "num_results": 0,
                    "retrieval_time_ms": retrieval_time
                },
                llm_provider="none",
                total_time_ms=(time.time() - start_time) * 1000
            )
        
        # Step 3: Assemble context
        assembled = self.answer_builder.assemble_context(results, include_metadata=True)
        logger.info(
            f"Assembled context: {assembled.sources_count} sources, "
            f"~{assembled.total_tokens} tokens"
        )
        
        # Step 4: Build prompt
        prompt = build_chat_prompt(query, assembled.formatted_context)
        
        # Step 5: Generate answer
        llm_start = time.time()
        answer = await self.llm_manager.generate(
            prompt,
            context_size=assembled.total_tokens,
            query_complexity=self._assess_complexity(query),
            provider_type=provider_type,
            temperature=temperature,
            max_tokens=2000
        )
        llm_time = (time.time() - llm_start) * 1000
        
        logger.info(f"Generated answer in {llm_time:.2f}ms")
        
        # Step 6: Build citations
        citations = self.answer_builder.build_citations(assembled.context_blocks)
        
        total_time = (time.time() - start_time) * 1000
        
        # Determine which provider was used
        selected_provider = self.llm_manager.auto_select_provider(
            assembled.total_tokens,
            self._assess_complexity(query),
            provider_type
        )
        
        return ChatResponse(
            answer=answer,
            citations=citations,
            retrieval_stats={
                "num_results": len(results),
                "retrieval_time_ms": retrieval_time,
                "sources_count": assembled.sources_count,
                "context_tokens": assembled.total_tokens
            },
            llm_provider=selected_provider.value,
            total_time_ms=total_time
        )
    
    async def explain_code(
        self,
        file_path: str,
        start_line: int,
        end_line: int
    ) -> ChatResponse:
        """
        Explain specific code section.
        
        Args:
            file_path: File path
            start_line: Start line
            end_line: End line
            
        Returns:
            ChatResponse with explanation
        """
        # Search for the specific code section
        query = f"code in {file_path} lines {start_line}-{end_line}"
        
        filter_criteria = FilterCriteria(
            path_prefix=file_path,
            line_range=(start_line, end_line)
        )
        
        return await self.chat(
            query=query,
            top_k=5,
            use_query_expansion=False,
            filter_criteria=filter_criteria
        )
    
    async def debug_assist(
        self,
        error_message: str,
        context_query: str = None
    ) -> ChatResponse:
        """
        Debugging assistance.
        
        Args:
            error_message: Error message
            context_query: Additional context query
            
        Returns:
            ChatResponse with debugging help
        """
        query = f"debug error: {error_message}"
        if context_query:
            query += f" {context_query}"
        
        return await self.chat(
            query=query,
            top_k=10,
            use_query_expansion=True,
            temperature=0.5  # Lower temperature for debugging
        )
    
    def _assess_complexity(self, query: str) -> str:
        """Assess query complexity."""
        query_lower = query.lower()
        
        # Complex indicators
        if any(word in query_lower for word in ["architecture", "design", "pattern", "why", "compare"]):
            return "complex"
        
        # Simple indicators
        if any(word in query_lower for word in ["what is", "show", "find", "where"]):
            return "simple"
        
        return "medium"
