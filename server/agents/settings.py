from pydantic_settings import BaseSettings
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # Ollama Configuration
    ollama_url: str = "http://localhost:11434"
    model_id: str = "gpt-oss:20b"
    
    # Server Configuration
    server_port: int = 8080
    ui_origin: str = "http://localhost:3000"
    allow_tools: bool = True
    
    # CORS Configuration
    allow_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    # Database Configuration
    database_path: str = "data/conversations.db"
    
    # RAG Configuration
    chromadb_path: str = "data/chromadb"
    embedding_model: str = "all-MiniLM-L6-v2"
    
    # Rate limiting
    max_requests_per_minute: int = 60
    max_requests_per_conversation: int = 10
    
    # MCP Configuration
    mcp_endpoints: Optional[str] = None  # Comma-separated list of "name:command" pairs
    
    # Tool Configuration
    max_web_pages_per_turn: int = 5
    max_html_size_mb: int = 2
    web_timeout_seconds: int = 10
    
    # Temperature and generation settings
    default_temperature: float = 0.7
    max_tokens: Optional[int] = None
    
    class Config:
        env_file = ".env"
        env_prefix = ""

settings = Settings()
