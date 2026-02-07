"""
Chat routes for DevMind API.
LLM-powered chat with retrieval augmentation.
"""

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import logging
import json

from devmind.core.container import get_container, DIContainer
from devmind.llm import ChatEngine, ChatResponse
from devmind.retrieval import FilterCriteria
from devmind.llm.provider import ProviderType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


# Request/Response models
class ChatRequest(BaseModel):
    """Chat request model."""
    query: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(default=10, gt=0, le=50)
    use_query_expansion: bool = Field(default=True)
    use_keyword_search: bool = Field(default=True)
    provider: Optional[str] = Field(default=None)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    filters: Optional[Dict[str, Any]] = None


class ChatResponseModel(BaseModel):
    """Chat response model."""
    answer: str
    citations: List[Dict[str, Any]]
    retrieval_stats: Dict[str, Any]
    llm_provider: str
    total_time_ms: float


class StreamChunk(BaseModel):
    """Streaming chunk model."""
    delta: str
    is_final: bool = False
    citations: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None


def get_di_container() -> DIContainer:
    """Dependency injection for container."""
    return get_container()


@router.post("", response_model=ChatResponseModel)
@router.post("/", response_model=ChatResponseModel)
async def chat(
    request: ChatRequest,
    container: DIContainer = Depends(get_di_container)
):
    """
    Chat endpoint with retrieval-augmented generation.
    
    Process:
    1. Expand query (optional)
    2. Retrieve relevant code/docs
    3. Assemble context
    4. Generate LLM response
    5. Return answer with citations
    """
    logger.info(f"Chat request: '{request.query}'")
    
    try:
        # Get chat engine
        chat_engine = container.get_chat_engine()
        
        # Convert filters if provided
        filter_criteria = None
        if request.filters:
            filter_criteria = FilterCriteria(**request.filters)
        
        # Parse provider
        provider_type = None
        if request.provider:
            try:
                provider_type = ProviderType(request.provider.lower())
            except ValueError:
                pass
        
        # Process chat
        response: ChatResponse = await chat_engine.chat(
            query=request.query,
            top_k=request.top_k,
            use_query_expansion=request.use_query_expansion,
            use_keyword_search=request.use_keyword_search,
            filter_criteria=filter_criteria,
            provider_type=provider_type,
            temperature=request.temperature
        )
        
        logger.info(f"Chat completed in {response.total_time_ms:.2f}ms")
        
        return ChatResponseModel(
            answer=response.answer,
            citations=response.citations,
            retrieval_stats=response.retrieval_stats,
            llm_provider=response.llm_provider,
            total_time_ms=response.total_time_ms
        )
        
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@router.websocket("/stream")
async def chat_stream(websocket: WebSocket):
    """
    WebSocket endpoint for streaming chat responses.
    
    Client sends:
    {
      "query": "...",
      "top_k": 10,
      "provider": "sonnet",
      ...
    }
    
    Server streams:
    {
      "delta": "partial text",
      "is_final": false
    }
    
    Final message:
    {
      "delta": "",
      "is_final": true,
      "citations": [...],
      "metadata": {...}
    }
    """
    await websocket.accept()
    logger.info("WebSocket connection established")
    
    try:
        # Get container
        container = get_container()
        
        # Receive request
        data = await websocket.receive_text()
        request_data = json.loads(data)
        
        query = request_data.get("query")
        top_k = request_data.get("top_k", 10)
        use_expansion = request_data.get("use_query_expansion", True)
        use_keyword = request_data.get("use_keyword_search", True)
        provider_str = request_data.get("provider")
        temperature = request_data.get("temperature", 0.7)
        
        logger.info(f"WebSocket chat: '{query}'")
        
        if not query:
            await websocket.send_json({
                "error": "Query is required",
                "is_final": True
            })
            await websocket.close()
            return
        
        # Get chat engine  
        chat_engine = container.get_chat_engine()
        llm_manager = container.get_llm_manager()
        
        # Parse provider
        provider_type = None
        if provider_str:
            try:
                provider_type = ProviderType(provider_str.lower())
            except ValueError:
                pass
        
        # Step 1: Retrieval (non-streaming)
        retrieval_pipeline = container.get_retrieval_pipeline()
        
        # Expand query if needed
        if use_expansion:
            from devmind.llm import QueryExpander
            expander = QueryExpander()
            expanded = expander.expand(query, max_variants=2)
            search_query = expanded[1] if len(expanded) > 1 else query
        else:
            search_query = query
        
        # Retrieve
        results = retrieval_pipeline.search(
            query=search_query,
            top_k=top_k,
            use_keyword=use_keyword
        )
        
        if not results:
            await websocket.send_json({
                "delta": "I couldn't find any relevant information in the codebase.",
                "is_final": True,
                "citations": [],
                "metadata": {"num_results": 0}
            })
            await websocket.close()
            return
        
        # Step 2: Assemble context
        from devmind.llm import AnswerBuilder
        from devmind.llm.prompts import build_chat_prompt
        
        answer_builder = AnswerBuilder(max_context_tokens=8000)
        assembled = answer_builder.assemble_context(results)
        
        # Step 3: Build prompt
        prompt = build_chat_prompt(query, assembled.formatted_context)
        
        # Step 4: Stream response
        full_answer = ""
        
        async for chunk in llm_manager.stream(
            prompt,
            context_size=assembled.total_tokens,
            query_complexity="medium",
            provider_type=provider_type,
            temperature=temperature
        ):
            full_answer += chunk
            
            # Send chunk
            await websocket.send_json({
                "delta": chunk,
                "is_final": False
            })
        
        # Step 5: Send final message with citations
        citations = answer_builder.build_citations(assembled.context_blocks)
        
        await websocket.send_json({
            "delta": "",
            "is_final": True,
            "citations": citations,
            "metadata": {
                "num_results": len(results),
                "sources_count": assembled.sources_count,
                "context_tokens": assembled.total_tokens
            }
        })
        
        logger.info("WebSocket chat completed")
        await websocket.close()
        
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        try:
            await websocket.send_json({
                "error": str(e),
                "is_final": True
            })
            await websocket.close()
        except:
            pass


@router.post("/explain", response_model=ChatResponseModel)
async def explain_code(
    file_path: str,
    start_line: int,
    end_line: int,
    container: DIContainer = Depends(get_di_container)
):
    """
    Explain specific code section.
    
    Args:
        file_path: File path
        start_line: Start line
        end_line: End line
    """
    logger.info(f"Explain code: {file_path}:{start_line}-{end_line}")
    
    try:
        chat_engine = container.get_chat_engine()
        
        response = await chat_engine.explain_code(
            file_path=file_path,
            start_line=start_line,
            end_line=end_line
        )
        
        return ChatResponseModel(
            answer=response.answer,
            citations=response.citations,
            retrieval_stats=response.retrieval_stats,
            llm_provider=response.llm_provider,
            total_time_ms=response.total_time_ms
        )
        
    except Exception as e:
        logger.error(f"Code explanation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/debug", response_model=ChatResponseModel)
async def debug_assist(
    error_message: str,
    context_query: str = None,
    container: DIContainer = Depends(get_di_container)
):
    """
    Debugging assistance.
    
    Args:
        error_message: Error message
        context_query: Optional context query
    """
    logger.info(f"Debug assist: {error_message}")
    
    try:
        chat_engine = container.get_chat_engine()
        
        response = await chat_engine.debug_assist(
            error_message=error_message,
            context_query=context_query
        )
        
        return ChatResponseModel(
            answer=response.answer,
            citations=response.citations,
            retrieval_stats=response.retrieval_stats,
            llm_provider=response.llm_provider,
            total_time_ms=response.total_time_ms
        )
        
    except Exception as e:
        logger.error(f"Debug assist error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
