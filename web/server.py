"""FastAPI server for the RAG chatbot web interface."""

import asyncio
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag.retriever import CodeRetriever, create_retriever

# Global retriever instance
retriever: Optional[CodeRetriever] = None


class QueryRequest(BaseModel):
    """Request model for queries."""

    question: str
    top_k: Optional[int] = None
    language: Optional[str] = None
    use_hybrid_search: bool = True


class QueryResponse(BaseModel):
    """Response model for queries."""

    answer: str
    sources: list[dict]
    query_intent: Optional[str] = None
    debug_info: Optional[dict] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize retriever on startup."""
    global retriever

    project_id = os.environ.get(
        "GCP_PROJECT_ID", os.environ.get("GOOGLE_CLOUD_PROJECT")
    )
    if not project_id:
        print("Warning: GCP_PROJECT_ID not set. RAG queries will fail.")
        yield
        return

    try:
        retriever = create_retriever(
            project_id=project_id,
            location=os.environ.get("GCP_LOCATION", "us-central1"),
            llm_model=os.environ.get("LLM_MODEL", "gemini-2.5-flash"),
            db_host=os.environ.get("PGHOST", "localhost"),
            db_port=int(os.environ.get("PGPORT", "5432")),
            db_name=os.environ.get("PGDATABASE", "codebase_rag"),
            db_user=os.environ.get("PGUSER", "postgres"),
            db_password=os.environ.get("PGPASSWORD", ""),
        )
        print("RAG retriever initialized successfully")
    except Exception as e:
        print(f"Failed to initialize retriever: {e}")

    yield

    # Cleanup
    if retriever and retriever.store:
        retriever.store.close()


app = FastAPI(
    title="Koda",
    description="Koda - Your intelligent codebase assistant",
    lifespan=lifespan,
)

# Mount static files
web_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=web_dir / "static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the main chat interface."""
    html_path = web_dir / "templates" / "index.html"
    return HTMLResponse(content=html_path.read_text())


@app.post("/api/query", response_model=QueryResponse)
async def query_endpoint(request: QueryRequest):
    """REST endpoint for queries."""
    if not retriever:
        return QueryResponse(
            answer="Error: RAG retriever not initialized. Check server configuration.",
            sources=[],
        )

    try:
        response = await asyncio.to_thread(
            retriever.query,
            question=request.question,
            top_k=request.top_k,
            language=request.language,
            use_hybrid_search=request.use_hybrid_search,
        )

        sources = [
            {
                "file_path": chunk.file_path,
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
                "class_name": chunk.class_name,
                "method_name": chunk.method_name,
                "chunk_type": chunk.chunk_type,
                "content_preview": chunk.content[:200] + "..."
                if len(chunk.content) > 200
                else chunk.content,
                "score": score,
            }
            for chunk, score in zip(response.sources, response.scores)
        ]

        return QueryResponse(
            answer=response.answer,
            sources=sources,
            query_intent=response.query_analysis.intent.value
            if response.query_analysis
            else None,
            debug_info={
                "model": response.model,
                "num_sources": len(response.sources),
                "num_dependencies": len(response.dependencies),
            },
        )
    except Exception as e:
        return QueryResponse(
            answer=f"Error processing query: {str(e)}",
            sources=[],
        )


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket endpoint for streaming chat."""
    await websocket.accept()

    if not retriever:
        await websocket.send_json(
            {
                "type": "error",
                "content": "RAG retriever not initialized. Check server configuration.",
            }
        )
        await websocket.close()
        return

    try:
        while True:
            data = await websocket.receive_json()
            question = data.get("question", "")

            if not question:
                await websocket.send_json(
                    {
                        "type": "error",
                        "content": "No question provided",
                    }
                )
                continue

            # Send thinking indicator
            await websocket.send_json(
                {
                    "type": "status",
                    "content": "Analyzing query...",
                }
            )

            try:
                # Run query in thread pool
                response = await asyncio.to_thread(
                    retriever.query,
                    question=question,
                    top_k=data.get("top_k"),
                    language=data.get("language"),
                    use_hybrid_search=data.get("use_hybrid_search", True),
                )

                # Send query analysis info
                if response.query_analysis:
                    await websocket.send_json(
                        {
                            "type": "analysis",
                            "content": {
                                "intent": response.query_analysis.intent.value,
                                "class_names": response.query_analysis.class_names,
                                "primary_terms": response.query_analysis.primary_terms[
                                    :5
                                ],
                            },
                        }
                    )

                # Send sources
                sources = [
                    {
                        "file_path": chunk.file_path,
                        "start_line": chunk.start_line,
                        "end_line": chunk.end_line,
                        "class_name": chunk.class_name,
                        "method_name": chunk.method_name,
                        "chunk_type": chunk.chunk_type,
                        "language": chunk.language,
                        "content": chunk.content,
                        "score": score,
                    }
                    for chunk, score in zip(response.sources, response.scores)
                ]

                await websocket.send_json(
                    {
                        "type": "sources",
                        "content": sources,
                    }
                )

                # Send the answer
                await websocket.send_json(
                    {
                        "type": "answer",
                        "content": response.answer,
                    }
                )

                # Send completion
                await websocket.send_json(
                    {
                        "type": "done",
                        "content": {
                            "model": response.model,
                            "num_sources": len(response.sources),
                        },
                    }
                )

            except Exception as e:
                await websocket.send_json(
                    {
                        "type": "error",
                        "content": f"Error: {str(e)}",
                    }
                )

    except WebSocketDisconnect:
        print("WebSocket disconnected")


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "retriever_initialized": retriever is not None,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "server:app",
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", "8080")),
        reload=True,
    )
