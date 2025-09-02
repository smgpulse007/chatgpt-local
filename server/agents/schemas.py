from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime

class Message(BaseModel):
    role: Literal["user", "assistant", "system", "tool"]
    content: str
    name: Optional[str] = None
    tool_call_id: Optional[str] = None

class ChatRequest(BaseModel):
    messages: List[Message]
    conversation_id: Optional[str] = None
    enable_browsing: bool = False
    system: Optional[str] = None
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    model: Optional[str] = None
    max_tokens: Optional[int] = None

class ChatResponse(BaseModel):
    content: str
    conversation_id: str
    tool_calls: Optional[List[Dict[str, Any]]] = None

class ModelInfo(BaseModel):
    name: str
    size: int
    modified_at: str

class HealthResponse(BaseModel):
    status: Literal["healthy", "unhealthy"]
    timestamp: str
    ollama_connected: bool
    model_id: str

class ConversationInfo(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int

class ToolCall(BaseModel):
    id: str
    type: Literal["function"]
    function: Dict[str, Any]

class ToolResult(BaseModel):
    tool_call_id: str
    content: str
    success: bool = True

# Tool parameter schemas
class WebSearchParams(BaseModel):
    query: str = Field(description="Search query")
    max_results: int = Field(default=5, ge=1, le=10, description="Maximum number of results")

class WebFetchParams(BaseModel):
    url: str = Field(description="URL to fetch")

class WebReadParams(BaseModel):
    url: str = Field(description="URL to read and extract content from")

class TimeNowParams(BaseModel):
    pass

class SystemInfoParams(BaseModel):
    pass

# Tool definitions for OpenAI-style function calling
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for recent information via DuckDuckGo",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "max_results": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 10,
                        "default": 5,
                        "description": "Maximum number of results"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_fetch",
            "description": "Fetch raw HTML content from a URL",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to fetch"
                    }
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_read",
            "description": "Read and extract clean text content from a webpage",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string", 
                        "description": "URL to read and extract content from"
                    }
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function", 
        "function": {
            "name": "time_now",
            "description": "Get the current date and time",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "system_info", 
            "description": "Get system information including hostname, platform, and Python version",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]
