from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator, Optional, Dict, Any
import httpx
import asyncio
import json
import logging
import uvicorn
from datetime import datetime
import os

from agents.settings import settings
from agents.schemas import ChatRequest, ChatResponse, ModelInfo, HealthResponse
from agents.core import Agent
from agents.memory import ConversationManager
from agents.util import create_sse_data

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Local ChatGPT API",
    description="Local ChatGPT-style agent with web browsing capabilities",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
agent = Agent()
conversation_manager = ConversationManager()

@app.on_event("startup")
async def startup_event():
    """Initialize database and ensure data directory exists"""
    os.makedirs("data", exist_ok=True)
    await conversation_manager.initialize()

@app.get("/healthz", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    try:
        # Test Ollama connection
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{settings.ollama_url}/api/tags", timeout=5.0)
            ollama_healthy = response.status_code == 200
    except Exception as e:
        logger.error(f"Ollama health check failed: {e}")
        ollama_healthy = False
    
    return HealthResponse(
        status="healthy" if ollama_healthy else "unhealthy",
        timestamp=datetime.utcnow().isoformat(),
        ollama_connected=ollama_healthy,
        model_id=settings.model_id
    )

@app.get("/models", response_model=list[ModelInfo])
async def list_models():
    """List available Ollama models"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{settings.ollama_url}/api/tags", timeout=10.0)
            if response.status_code != 200:
                raise HTTPException(status_code=503, detail="Ollama service unavailable")
            
            data = response.json()
            models = []
            for model in data.get("models", []):
                models.append(ModelInfo(
                    name=model["name"],
                    size=model.get("size", 0),
                    modified_at=model.get("modified_at", "")
                ))
            
            return models
    except httpx.RequestError as e:
        logger.error(f"Failed to fetch models: {e}")
        raise HTTPException(status_code=503, detail="Ollama service unavailable")

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """Main chat endpoint with streaming response"""
    try:
        # Validate conversation exists or create new one
        if request.conversation_id:
            conversation = await conversation_manager.get_conversation(request.conversation_id)
            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found")
        else:
            # Create new conversation
            conversation_id = await conversation_manager.create_conversation(
                title=request.messages[0].content[:50] if request.messages else "New Chat"
            )
            request.conversation_id = conversation_id

        # Save user message
        if request.messages:
            last_message = request.messages[-1]
            if last_message.role == "user":
                await conversation_manager.add_message(
                    request.conversation_id,
                    "user",
                    last_message.content
                )

        # Generate streaming response
        return StreamingResponse(
            stream_chat_response(request),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
            }
        )
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def stream_chat_response(request: ChatRequest) -> AsyncGenerator[str, None]:
    """Stream chat response using Server-Sent Events"""
    try:
        # Run agent with streaming
        response_content = ""
        async for chunk in agent.run_streaming(
            messages=request.messages,
            conversation_id=request.conversation_id,
            enable_browsing=request.enable_browsing,
            system=request.system,
            temperature=request.temperature,
            model=request.model or settings.model_id
        ):
            if chunk.get("type") == "token":
                response_content += chunk.get("content", "")
                yield create_sse_data(chunk)
            elif chunk.get("type") == "tool_call":
                yield create_sse_data(chunk)
            elif chunk.get("type") == "tool_result":
                yield create_sse_data(chunk)
            elif chunk.get("type") == "error":
                yield create_sse_data(chunk)
                return

        # Save assistant response
        if response_content and request.conversation_id:
            await conversation_manager.add_message(
                request.conversation_id,
                "assistant",
                response_content
            )

        # Send completion signal
        yield create_sse_data({"type": "done"})

    except Exception as e:
        logger.error(f"Streaming error: {e}")
        yield create_sse_data({
            "type": "error",
            "content": f"An error occurred: {str(e)}"
        })

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time chat"""
    await websocket.accept()
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            try:
                request_data = json.loads(data)
                request = ChatRequest(**request_data)
                
                # Process with agent
                async for chunk in agent.run_streaming(
                    messages=request.messages,
                    conversation_id=request.conversation_id,
                    enable_browsing=request.enable_browsing,
                    system=request.system,
                    temperature=request.temperature,
                    model=request.model or settings.model_id
                ):
                    await websocket.send_text(json.dumps(chunk))
                
                # Send completion
                await websocket.send_text(json.dumps({"type": "done"}))
                
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "content": "Invalid JSON format"
                }))
            except Exception as e:
                await websocket.send_text(json.dumps({
                    "type": "error", 
                    "content": str(e)
                }))
                
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")

@app.get("/conversations")
async def list_conversations():
    """List all conversations"""
    conversations = await conversation_manager.list_conversations()
    return conversations

@app.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(conversation_id: str):
    """Get messages for a specific conversation"""
    messages = await conversation_manager.get_messages(conversation_id)
    return messages

@app.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation"""
    await conversation_manager.delete_conversation(conversation_id)
    return {"message": "Conversation deleted"}

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=settings.server_port,
        log_level="info",
        reload=True
    )
