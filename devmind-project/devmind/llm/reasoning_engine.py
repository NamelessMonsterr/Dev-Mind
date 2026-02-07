"""
Reasoning Engine for DevMind.
Multi-step deliberate reasoning (R1-style).
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging

from devmind.retrieval import RetrievalPipeline, RetrievalResult
from devmind.llm.provider import LLMProviderManager
from devmind.llm.prompts import build_reasoning_prompt

logger = logging.getLogger(__name__)


@dataclass
class ReasoningStep:
    """Single reasoning step."""
    step_number: int
    thought: str
    action: str  # "retrieve", "analyze", "conclude"
    result: Optional[str] = None


@dataclass
class ReasoningChain:
    """Complete reasoning chain."""
    query: str
    steps: List[ReasoningStep]
    final_answer: str
    confidence: float


class ReasoningEngine:
    """
    Multi-step reasoning engine (R1-style).
    
    Implements deliberate reasoning with retrieval refinement.
    """
    
    def __init__(
        self,
        retrieval_pipeline: RetrievalPipeline,
        llm_manager: LLMProviderManager,
        max_steps: int = 5
    ):
        """
        Initialize reasoning engine.
        
        Args:
            retrieval_pipeline: Retrieval pipeline for context
            llm_manager: LLM provider manager
            max_steps: Maximum reasoning steps
        """
        self.retrieval_pipeline = retrieval_pipeline
        self.llm_manager = llm_manager
        self.max_steps = max_steps
        
        logger.info(f"ReasoningEngine initialized (max_steps={max_steps})")
    
    async def reason(
        self,
        query: str,
        initial_results: List[RetrievalResult]
    ) -> ReasoningChain:
        """
        Perform multi-step reasoning.
        
        Args:
            query: User query
            initial_results: Initial retrieval results
            
        Returns:
            Complete reasoning chain
        """
        logger.info(f"Starting reasoning for: '{query}'")
        
        steps = []
        current_context = initial_results
        
        # Step 1: Assess relevance
        step1 = await self._assess_relevance(query, current_context)
        steps.append(step1)
        
        # Step 2: Check completeness
        step2 = await self._check_completeness(query, current_context, step1.result)
        steps.append(step2)
        
        # Step 3: Refine if needed
        if "incomplete" in step2.result.lower():
            step3 = await self._refine_retrieval(query, current_context)
            steps.append(step3)
            
            # Re-retrieve with refined query
            if step3.result:
                refined_results = self.retrieval_pipeline.search(step3.result, top_k=10)
                current_context.extend(refined_results)
        
        # Step 4: Synthesize answer
        step4 = await self._synthesize_answer(query, current_context)
        steps.append(step4)
        
        # Build final chain
        chain = ReasoningChain(
            query=query,
            steps=steps,
            final_answer=step4.result or "Unable to determine answer",
            confidence=self._calculate_confidence(steps)
        )
        
        logger.info(f"Reasoning complete: {len(steps)} steps, confidence={chain.confidence:.2f}")
        
        return chain
    
    async def _assess_relevance(
        self,
        query: str,
        results: List[RetrievalResult]
    ) -> ReasoningStep:
        """Assess if retrieved context is relevant."""
        logger.debug("Step 1: Assessing relevance")
        
        # Build context summary
        context_summary = "\n".join([
            f"- {r.file_path}: {r.section_type} (score: {r.score:.2f})"
            for r in results[:5]
        ])
        
        prompt = f"""Query: {query}

Retrieved context:
{context_summary}

Assess: Are these results relevant to the query?
Answer with "RELEVANT" or "NOT_RELEVANT" and brief explanation."""
        
        try:
            result = await self.llm_manager.generate(
                prompt,
                context_size=len(prompt),
                query_complexity="simple",
                temperature=0.3,
                max_tokens=200
            )
            
            return ReasoningStep(
                step_number=1,
                thought="Assessing relevance of retrieved context",
                action="analyze",
                result=result
            )
        except Exception as e:
            logger.error(f"Relevance assessment failed: {e}")
            return ReasoningStep(
                step_number=1,
                thought="Assessing relevance of retrieved context",
                action="analyze",
                result="RELEVANT (default)"
            )
    
    async def _check_completeness(
        self,
        query: str,
        results: List[RetrievalResult],
        relevance_result: str
    ) -> ReasoningStep:
        """Check if context is complete enough."""
        logger.debug("Step 2: Checking completeness")
        
        prompt = f"""Query: {query}

Relevance: {relevance_result}

Number of results: {len(results)}

Is the information complete enough to answer the query?
Answer with "COMPLETE" or "INCOMPLETE" and what's missing."""
        
        try:
            result = await self.llm_manager.generate(
                prompt,
                context_size=len(prompt),
                query_complexity="simple",
                temperature=0.3,
                max_tokens=200
            )
            
            return ReasoningStep(
                step_number=2,
                thought="Checking if context is complete",
                action="analyze",
                result=result
            )
        except Exception as e:
            logger.error(f"Completeness check failed: {e}")
            return ReasoningStep(
                step_number=2,
                thought="Checking if context is complete",
                action="analyze",
                result="COMPLETE (default)"
            )
    
    async def _refine_retrieval(
        self,
        query: str,
        current_results: List[RetrievalResult]
    ) -> ReasoningStep:
        """Refine query for better retrieval."""
        logger.debug("Step 3: Refining retrieval")
        
        prompt = f"""Original query: {query}

Current results are incomplete. Generate a refined query that would retrieve better results.

Refined query:"""
        
        try:
            result = await self.llm_manager.generate(
                prompt,
                context_size=len(prompt),
                query_complexity="simple",
                temperature=0.5,
                max_tokens=100
            )
            
            return ReasoningStep(
                step_number=3,
                thought="Refining query for better retrieval",
                action="retrieve",
                result=result.strip()
            )
        except Exception as e:
            logger.error(f"Query refinement failed: {e}")
            return ReasoningStep(
                step_number=3,
                thought="Refining query for better retrieval",
                action="retrieve",
                result=query  # Fall back to original
            )
    
    async def _synthesize_answer(
        self,
        query: str,
        results: List[RetrievalResult]
    ) -> ReasoningStep:
        """Synthesize final answer."""
        logger.debug("Step 4: Synthesizing answer")
        
        # Build context
        context = "\n\n".join([
            f"[{r.file_path}:{r.start_line}-{r.end_line}]\n{r.content}"
            for r in results[:10]
        ])
        
        prompt = build_reasoning_prompt(query, context)
        
        try:
            result = await self.llm_manager.generate(
                prompt,
                context_size=len(context),
                query_complexity="medium",
                temperature=0.7,
                max_tokens=1000
            )
            
            return ReasoningStep(
                step_number=4,
                thought="Synthesizing final answer from context",
                action="conclude",
                result=result
            )
        except Exception as e:
            logger.error(f"Answer synthesis failed: {e}")
            return ReasoningStep(
                step_number=4,
                thought="Synthesizing final answer from context",
                action="conclude",
                result="Error generating answer"
            )
    
    def _calculate_confidence(self, steps: List[ReasoningStep]) -> float:
        """Calculate confidence score."""
        # Simple heuristic: higher confidence if relevant and complete
        confidence = 0.5
        
        for step in steps:
            if step.result and "relevant" in step.result.lower():
                confidence += 0.2
            if step.result and "complete" in step.result.lower():
                confidence += 0.3
        
        return min(confidence, 1.0)
