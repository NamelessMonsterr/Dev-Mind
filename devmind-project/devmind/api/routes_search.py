"""
Search routes for DevMind API.
Endpoints for semantic + keyword hybrid search.
"""

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime
import time
import logging

from devmind.api.models import (
    SearchRequest,
    SearchResponse,
    SearchResultModel,
    FilterCriteriaModel
)
from devmind.core.container import get_container, DIContainer
from devmind.retrieval import FilterCriteria

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["search"])


def get_di_container() -> DIContainer:
    """Dependency injection for container."""
    return get_container()


def convert_filter_criteria(filters: FilterCriteriaModel) -> FilterCriteria:
    """Convert API filter model to retrieval filter criteria."""
    return FilterCriteria(
        file_types=filters.file_types,
        languages=filters.languages,
        path_prefix=filters.path_prefix,
        path_excludes=filters.path_excludes,
        min_score=filters.min_score,
        max_results=filters.max_results,
        line_range=filters.line_range,
        section_types=filters.section_types
    )


@router.post("", response_model=SearchResponse)
@router.post("/", response_model=SearchResponse)
async def search(
    request: SearchRequest,
    container: DIContainer = Depends(get_di_container)
):
    """
    Universal search across all indices.
    
    Performs hybrid semantic + keyword search with optional filtering.
    """
    logger.info(f"Search request: '{request.query}' (top_k={request.top_k})")
    
    start_time = time.time()
    
    try:
        # Get retrieval pipeline
        pipeline = container.get_retrieval_pipeline()
        
        # Convert filters
        filter_criteria = None
        if request.filters:
            filter_criteria = convert_filter_criteria(request.filters)
        
        # Perform search
        results = pipeline.search(
            query=request.query,
            top_k=request.top_k,
            use_keyword=request.use_keyword_search,
            filter_criteria=filter_criteria
        )
        
        # Calculate search time
        search_time_ms = (time.time() - start_time) * 1000
        
        # Record statistics
        container.record_search(search_time_ms)
        
        # Convert results to response model
        result_models = [
            SearchResultModel(
                score=r.score,
                content=r.content,
                file_path=r.file_path,
                start_line=r.start_line,
                end_line=r.end_line,
                section_type=r.section_type,
                language=r.language,
                chunk_id=r.chunk_id,
                index_name=r.index_name,
                matched_terms=r.matched_terms,
                vector_score=r.vector_score,
                keyword_score=r.keyword_score
            )
            for r in results
        ]
        
        logger.info(f"Found {len(result_models)} results in {search_time_ms:.2f}ms")
        
        return SearchResponse(
            query=request.query,
            results=result_models,
            total_results=len(result_models),
            search_time_ms=search_time_ms,
            filters_applied=request.filters is not None
        )
        
    except Exception as e:
        logger.error(f"Search error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.post("/code", response_model=SearchResponse)
async def search_code(
    request: SearchRequest,
    container: DIContainer = Depends(get_di_container)
):
    """
    Search code index only.
    
    Restricts search to code chunks (functions, classes, methods).
    """
    logger.info(f"Code search: '{request.query}'")
    
    start_time = time.time()
    
    try:
        pipeline = container.get_retrieval_pipeline()
        
        # Convert filters
        filter_criteria = None
        if request.filters:
            filter_criteria = convert_filter_criteria(request.filters)
        
        # Search code index
        results = pipeline.search(
            query=request.query,
            top_k=request.top_k,
            use_keyword=request.use_keyword_search,
            filter_criteria=filter_criteria,
            index_name="code"
        )
        
        search_time_ms = (time.time() - start_time) * 1000
        container.record_search(search_time_ms)
        
        result_models = [
            SearchResultModel(
                score=r.score,
                content=r.content,
                file_path=r.file_path,
                start_line=r.start_line,
                end_line=r.end_line,
                section_type=r.section_type,
                language=r.language,
                chunk_id=r.chunk_id,
                index_name=r.index_name,
                matched_terms=r.matched_terms,
                vector_score=r.vector_score,
                keyword_score=r.keyword_score
            )
            for r in results
        ]
        
        return SearchResponse(
            query=request.query,
            results=result_models,
            total_results=len(result_models),
            search_time_ms=search_time_ms,
            filters_applied=request.filters is not None
        )
        
    except Exception as e:
        logger.error(f"Code search error: {e}")
        raise HTTPException(status_code=500, detail=f"Code search failed: {str(e)}")


@router.post("/docs", response_model=SearchResponse)
async def search_docs(
    request: SearchRequest,
    container: DIContainer = Depends(get_di_container)
):
    """
    Search documentation index only.
    
    Restricts search to documentation chunks (markdown, text files).
    """
    logger.info(f"Docs search: '{request.query}'")
    
    start_time = time.time()
    
    try:
        pipeline = container.get_retrieval_pipeline()
        
        filter_criteria = None
        if request.filters:
            filter_criteria = convert_filter_criteria(request.filters)
        
        results = pipeline.search(
            query=request.query,
            top_k=request.top_k,
            use_keyword=request.use_keyword_search,
            filter_criteria=filter_criteria,
            index_name="docs"
        )
        
        search_time_ms = (time.time() - start_time) * 1000
        container.record_search(search_time_ms)
        
        result_models = [
            SearchResultModel(**r.to_dict())
            for r in results
        ]
        
        return SearchResponse(
            query=request.query,
            results=result_models,
            total_results=len(result_models),
            search_time_ms=search_time_ms,
            filters_applied=request.filters is not None
        )
        
    except Exception as e:
        logger.error(f"Docs search error: {e}")
        raise HTTPException(status_code=500, detail=f"Docs search failed: {str(e)}")


@router.post("/notes", response_model=SearchResponse)
async def search_notes(
    request: SearchRequest,
    container: DIContainer = Depends(get_di_container)
):
    """
    Search notes index only.
    
    Restricts search to notes/comments.
    """
    logger.info(f"Notes search: '{request.query}'")
    
    start_time = time.time()
    
    try:
        pipeline = container.get_retrieval_pipeline()
        
        filter_criteria = None
        if request.filters:
            filter_criteria = convert_filter_criteria(request.filters)
        
        results = pipeline.search(
            query=request.query,
            top_k=request.top_k,
            use_keyword=request.use_keyword_search,
            filter_criteria=filter_criteria,
            index_name="notes"
        )
        
        search_time_ms = (time.time() - start_time) * 1000
        container.record_search(search_time_ms)
        
        result_models = [
            SearchResultModel(**r.to_dict())
            for r in results
        ]
        
        return SearchResponse(
            query=request.query,
            results=result_models,
            total_results=len(result_models),
            search_time_ms=search_time_ms,
            filters_applied=request.filters is not None
        )
        
    except Exception as e:
        logger.error(f"Notes search error: {e}")
        raise HTTPException(status_code=500, detail=f"Notes search failed: {str(e)}")


@router.post("/functions", response_model=SearchResponse)
async def search_functions(
    request: SearchRequest,
    container: DIContainer = Depends(get_di_container)
):
    """
    Search for functions only.
    
    Filters results to function and method sections.
    """
    logger.info(f"Function search: '{request.query}'")
    
    start_time = time.time()
    
    try:
        pipeline = container.get_retrieval_pipeline()
        
        results = pipeline.search_functions(
            query=request.query,
            top_k=request.top_k
        )
        
        search_time_ms = (time.time() - start_time) * 1000
        container.record_search(search_time_ms)
        
        result_models = [
            SearchResultModel(**r.to_dict())
            for r in results
        ]
        
        return SearchResponse(
            query=request.query,
            results=result_models,
            total_results=len(result_models),
            search_time_ms=search_time_ms,
            filters_applied=True
        )
        
    except Exception as e:
        logger.error(f"Function search error: {e}")
        raise HTTPException(status_code=500, detail=f"Function search failed: {str(e)}")


@router.post("/classes", response_model=SearchResponse)
async def search_classes(
    request: SearchRequest,
    container: DIContainer = Depends(get_di_container)
):
    """
    Search for classes only.
    
    Filters results to class sections.
    """
    logger.info(f"Class search: '{request.query}'")
    
    start_time = time.time()
    
    try:
        pipeline = container.get_retrieval_pipeline()
        
        results = pipeline.search_classes(
            query=request.query,
            top_k=request.top_k
        )
        
        search_time_ms = (time.time() - start_time) * 1000
        container.record_search(search_time_ms)
        
        result_models = [
            SearchResultModel(**r.to_dict())
            for r in results
        ]
        
        return SearchResponse(
            query=request.query,
            results=result_models,
            total_results=len(result_models),
            search_time_ms=search_time_ms,
            filters_applied=True
        )
        
    except Exception as e:
        logger.error(f"Class search error: {e}")
        raise HTTPException(status_code=500, detail=f"Class search failed: {str(e)}")
