"""Koda API Backend - FastAPI server for RAG chat interface."""

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

import yaml
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from starlette.websockets import WebSocketDisconnect as StarletteWebSocketDisconnect

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.rag import CodeRetriever
from src.rag.embedder import VertexEmbedder
from src.rag.vector_store import PgVectorStore
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


def load_config():
    """Load configuration from config.yaml."""
    # Try to find config.yaml
    config_paths = [
        Path("/app/config/config.yaml"),  # Docker path
        Path(__file__).parent.parent / "config" / "config.yaml",  # Relative path
        Path("config/config.yaml"),  # Current directory
    ]
    
    for config_path in config_paths:
        if config_path.exists():
            try:
                with open(config_path) as f:
                    return yaml.safe_load(f)
            except Exception as e:
                print(f"Warning: Failed to load config from {config_path}: {e}")
    
    return None


def get_retriever() -> Optional[CodeRetriever]:
    """Get or initialize the RAG retriever."""
    global retriever
    if retriever is None:
        # Try to load from config file first
        cfg = load_config()
        
        if cfg:
            gcp_config = cfg.get("gcp", {})
            rag_config = cfg.get("rag", {})
            project_id = gcp_config.get("project_id")
            location = gcp_config.get("location", "us-central1")
            llm_model = rag_config.get("llm_model", os.environ.get("LLM_MODEL", "gemini-2.5-flash"))
            embedding_model = rag_config.get("embedding_model", "text-embedding-005")
        else:
            # Fall back to environment variables
            project_id = os.environ.get("GCP_PROJECT_ID")
            location = os.environ.get("GCP_LOCATION", "us-central1")
            llm_model = os.environ.get("LLM_MODEL", "gemini-2.5-flash")
            embedding_model = "text-embedding-005"
        
        if not project_id or project_id == "YOUR_PROJECT_ID":
            print("WARNING: GCP_PROJECT_ID not set in config.yaml or environment, retriever unavailable")
            return None
        
        try:
            # Initialize embedder
            embedder = VertexEmbedder(
                project_id=project_id,
                location=location,
                model=embedding_model,
            )
            
            # Initialize vector store
            store = PgVectorStore()
            store.connect()
            
            # Initialize retriever
            retriever = CodeRetriever(
                embedder=embedder,
                store=store,
                llm_model=llm_model,
            )
            print(f"RAG Retriever initialized successfully (project: {project_id}, model: {llm_model})")
        except Exception as e:
            print(f"Failed to initialize retriever: {e}")
            import traceback
            traceback.print_exc()
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


async def send_safe(websocket: WebSocket, data: dict) -> bool:
    """Safely send JSON to websocket, return False if connection closed."""
    try:
        await websocket.send_json(data)
        return True
    except (WebSocketDisconnect, StarletteWebSocketDisconnect) as e:
        print(f"[DEBUG] Client disconnected (WebSocketDisconnect): {type(e).__name__}")
        return False
    except Exception as e:
        # Don't treat all exceptions as disconnects - log and return False
        error_type = type(e).__name__
        error_msg = str(e)
        # Only treat connection-related errors as disconnects
        if "not connected" in error_msg.lower() or "closed" in error_msg.lower():
            print(f"[DEBUG] Connection error: {error_type}: {error_msg}")
            return False
        else:
            # Other errors (like serialization) should be logged but not treated as disconnect
            print(f"[WARNING] Error sending message (not a disconnect): {error_type}: {error_msg}")
            return False


async def send_progress(websocket: WebSocket, step: str, message: str) -> bool:
    """Send progress update, return False if connection closed."""
    return await send_safe(websocket, {
        "type": "status",
        "content": message
    })


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket endpoint for chat."""
    await websocket.accept()

    ret = get_retriever()
    if ret is None:
        try:
            await websocket.send_json(
                {
                    "type": "error",
                    "content": "RAG retriever not available. Check GCP_PROJECT_ID configuration.",
                }
            )
            await websocket.close()
        except:
            pass
        return

    try:
        while True:
            try:
                # Set a longer timeout for receiving messages (30 seconds)
                data = await asyncio.wait_for(websocket.receive_json(), timeout=30.0)
            except asyncio.TimeoutError:
                # Send a ping to keep connection alive
                try:
                    await websocket.send_json({"type": "status", "content": "Still processing..."})
                    continue
                except:
                    print("[DEBUG] Connection lost during timeout, breaking")
                    break
            except (WebSocketDisconnect, StarletteWebSocketDisconnect) as e:
                print(f"[DEBUG] Client disconnected while receiving message: {type(e).__name__}")
                break
            except Exception as e:
                print(f"[ERROR] Error receiving message: {type(e).__name__}: {e}")
                break
            
            question = data.get("question", "")
            print(f"[DEBUG] Received query: {question[:50]}...")

            if not question:
                if not await send_safe(websocket, {"type": "error", "content": "No question provided"}):
                    break
                continue

            # Step 1: Analyze query
            client_connected = True
            if not await send_progress(websocket, "analyzing", "Analyzing your question..."):
                print("[DEBUG] Client disconnected during analysis step, but continuing query...")
                client_connected = False
            
            analysis = analyze_query(question)

            # Send analysis info
            if client_connected and not await send_safe(websocket, {
                "type": "analysis",
                "content": {
                    "intent": analysis.intent.value,
                    "primary_terms": analysis.primary_terms,
                    "class_names": analysis.class_names,
                }
            }):
                print("[DEBUG] Client disconnected during analysis send, but continuing query...")
                client_connected = False

            # Determine query type for better progress messages
            query_type = "general"
            if analysis.intent.value == "schema":
                query_type = "schema"
            elif analysis.intent.value in ["list", "count"]:
                query_type = "list"
            elif analysis.class_names:
                query_type = "class_lookup"
            
            # Track if client is still connected
            client_connected = True
            
            try:
                print(f"[DEBUG] Processing query: {question[:100]}...")
                
                # Step 2: Start query with type-specific message
                if query_type == "schema":
                    msg = f"Retrieving complete class definition for {analysis.class_names[0] if analysis.class_names else 'class'}..."
                elif query_type == "list":
                    msg = "Retrieving complete list of all classes from database..."
                elif query_type == "class_lookup":
                    msg = f"Looking up {analysis.class_names[0]} and related code..."
                else:
                    msg = f"Searching codebase for: {', '.join(analysis.primary_terms[:3])}..."
                
                if not await send_progress(websocket, "searching", msg):
                    print("[DEBUG] Client disconnected during initial search message")
                    client_connected = False
                
                # Removed "start" message - not needed, frontend handles status messages
                
                # Step 3: Embedding and searching
                if client_connected and not await send_progress(websocket, "embedding", "Generating query embedding..."):
                    print("[DEBUG] Client disconnected during embedding step, but continuing query...")
                    client_connected = False
                
                # Small delay to show the message
                if client_connected:
                    await asyncio.sleep(0.1)
                
                if client_connected and not await send_progress(websocket, "searching_db", "Searching vector database for relevant code..."):
                    print("[DEBUG] Client disconnected during search step, but continuing query...")
                    client_connected = False
                
                # Run query in thread pool with timeout to prevent hanging
                # Continue even if client disconnected - we want to see if query completes
                loop = asyncio.get_event_loop()
                
                # Send status update before starting long-running query
                if client_connected:
                    await send_progress(websocket, "generating", "Generating answer with LLM...")
                
                # Add timeout (60 seconds should be enough for most queries)
                try:
                    print("[DEBUG] Starting query execution in executor...")
                    
                    def execute_query():
                        try:
                            print("[DEBUG] Executor: Calling ret.query()...")
                            result = ret.query(
                                question=question,
                                top_k=data.get("top_k", 10),
                                include_sources=True,
                                use_hybrid_search=True,
                            )
                            print(f"[DEBUG] Executor: Query completed, answer length: {len(result.answer)}")
                            return result
                        except Exception as e:
                            print(f"[ERROR] Executor: Query failed: {e}")
                            import traceback
                            traceback.print_exc()
                            raise
                    
                    # Create a task to send periodic keepalive messages
                    async def send_keepalive():
                        keepalive_messages = [
                            "Analyzing code patterns...",
                            "Generating comprehensive answer...",
                            "Almost done...",
                        ]
                        for i, msg in enumerate(keepalive_messages * 10):  # Repeat for up to 60 seconds
                            await asyncio.sleep(2)  # Send every 2 seconds
                            if client_connected:
                                if not await send_progress(websocket, "generating", msg):
                                    break
                    
                    # Start keepalive task
                    keepalive_task = None
                    if client_connected:
                        keepalive_task = asyncio.create_task(send_keepalive())
                    
                    try:
                        response = await asyncio.wait_for(
                            loop.run_in_executor(None, execute_query),
                            timeout=60.0,
                        )
                        print(f"[DEBUG] Query completed successfully, answer length: {len(response.answer)}")
                    finally:
                        # Cancel keepalive task when query completes
                        if keepalive_task and not keepalive_task.done():
                            keepalive_task.cancel()
                            try:
                                await keepalive_task
                            except asyncio.CancelledError:
                                pass
                    
                    # If client disconnected, log but don't try to send
                    if not client_connected:
                        print(f"[DEBUG] Query completed but client already disconnected. Answer preview: {response.answer[:100]}...")
                        break
                    
                    # Step 4: Show what was found
                    if client_connected:
                        if not await send_progress(websocket, "found", f"Found {len(response.sources)} relevant code snippets"):
                            client_connected = False
                            print("[DEBUG] Client disconnected after finding results")
                    
                    if client_connected:
                        await asyncio.sleep(0.1)
                    
                    # Step 5: Generating answer (already done, just notify)
                    if client_connected:
                        if not await send_progress(websocket, "generating", "Answer generated!"):
                            client_connected = False
                    
                except asyncio.TimeoutError:
                    print("[ERROR] Query timed out after 60 seconds")
                    if client_connected:
                        await send_progress(websocket, "error", "Query timed out after 60 seconds")
                        await send_safe(websocket, {
                            "type": "error",
                            "content": "Query timed out after 60 seconds. Please try a simpler query or check server logs.",
                        })
                        await send_safe(websocket, {"type": "done"})
                    continue
                except Exception as query_error:
                    print(f"[ERROR] Query execution failed: {query_error}")
                    import traceback
                    traceback.print_exc()
                    if client_connected:
                        await send_safe(websocket, {
                            "type": "error",
                            "content": f"Query failed: {str(query_error)}"
                        })
                        await send_safe(websocket, {"type": "done"})
                    continue

                # Step 6: Send the response (only if client still connected)
                if not client_connected:
                    print("[DEBUG] Skipping response send - client disconnected")
                    break
                
                if not await send_progress(websocket, "complete", "Answer generated successfully!"):
                    break
                
                if not await send_safe(websocket, {
                    "type": "answer",
                    "content": response.answer,
                }):
                    break

                # Send sources
                if not await send_progress(websocket, "sources", f"Preparing {len(response.sources)} source references..."):
                    break
                
                sources = []
                for chunk in response.sources:
                    sources.append(
                        {
                            "file_path": chunk.file_path,
                            "start_line": chunk.start_line,
                            "end_line": chunk.end_line,
                            "chunk_type": chunk.chunk_type,
                            "name": chunk.class_name or chunk.method_name or chunk.file_path,
                            "content": chunk.content[:500] if chunk.content else "",
                        }
                    )

                if not await send_safe(websocket, {
                    "type": "sources",
                    "content": sources,
                }):
                    break

                await send_safe(websocket, {"type": "done"})
                print("[DEBUG] Query completed and sent to client successfully")

            except Exception as e:
                error_msg = str(e)
                print(f"[ERROR] Query error: {error_msg}")
                import traceback
                traceback.print_exc()
                await send_safe(websocket, {
                    "type": "error",
                    "content": f"Query failed: {error_msg}"
                })
                await send_safe(websocket, {"type": "done"})  # Ensure done is sent even on error

    except (WebSocketDisconnect, StarletteWebSocketDisconnect) as e:
        print(f"[DEBUG] Client disconnected: {e}")
    except Exception as e:
        print(f"[ERROR] WebSocket error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
