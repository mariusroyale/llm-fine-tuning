"""Koda API Backend - FastAPI server for RAG chat interface."""

import asyncio
import os
import sys
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.rag import CodeRetriever
from src.rag.query_analyzer import analyze_query

app = FastAPI(title="Koda API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global retriever instance
retriever: Optional[CodeRetriever] = None


def get_retriever() -> Optional[CodeRetriever]:
    """Get or initialize the RAG retriever."""
    global retriever
    if retriever is None:
        project_id = os.environ.get("GCP_PROJECT_ID")
        if not project_id:
            print("WARNING: GCP_PROJECT_ID not set, retriever unavailable")
            return None
        try:
            retriever = CodeRetriever(
                project_id=project_id,
                location=os.environ.get("GCP_LOCATION", "us-central1"),
                model_id=os.environ.get("LLM_MODEL", "gemini-2.5-flash"),
            )
            print("RAG Retriever initialized successfully")
        except Exception as e:
            print(f"Failed to initialize retriever: {e}")
            return None
    return retriever


class HealthResponse(BaseModel):
    status: str
    retriever_ready: bool


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    ret = get_retriever()
    return HealthResponse(status="ok", retriever_ready=ret is not None)


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket endpoint for chat."""
    await websocket.accept()

    ret = get_retriever()
    if ret is None:
        await websocket.send_json(
            {
                "type": "error",
                "message": "RAG retriever not available. Check GCP_PROJECT_ID configuration.",
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
                    {"type": "error", "message": "No question provided"}
                )
                continue

            # Analyze query for intent
            analysis = analyze_query(question)

            # Send analysis info
            await websocket.send_json(
                {
                    "type": "analysis",
                    "intent": analysis.intent.value,
                    "primary_terms": analysis.primary_terms,
                    "expanded_terms": analysis.expanded_terms[:10],
                }
            )

            # Stream the response
            await websocket.send_json({"type": "start"})

            try:
                # Run query in thread pool to not block
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: ret.query(
                        question=question,
                        top_k=data.get("top_k", 10),
                        include_sources=True,
                        use_hybrid_search=True,
                    ),
                )

                # Send the response
                await websocket.send_json(
                    {
                        "type": "content",
                        "content": response.answer,
                    }
                )

                # Send sources
                sources = []
                for chunk in response.chunks:
                    sources.append(
                        {
                            "file_path": chunk.file_path,
                            "start_line": chunk.start_line,
                            "end_line": chunk.end_line,
                            "chunk_type": chunk.chunk_type,
                            "name": chunk.name,
                            "content": chunk.content[:500] if chunk.content else "",
                        }
                    )

                await websocket.send_json(
                    {
                        "type": "sources",
                        "sources": sources,
                    }
                )

                await websocket.send_json({"type": "done"})

            except Exception as e:
                await websocket.send_json(
                    {"type": "error", "message": f"Query failed: {str(e)}"}
                )

    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
