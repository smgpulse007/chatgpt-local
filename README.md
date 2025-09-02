# Local ChatGPT - AI Agent with Web Browsing

A local ChatGPT-style application that runs entirely on your machine using **Ollama** for inference, with web browsing capabilities and a modern chat interface.

## Features

- 🤖 **Local AI**: Powered by Ollama (default: `gpt-oss:20b`)
- 🌐 **Web Browsing**: Search, fetch, and read web content via DuckDuckGo
- 🔧 **Tool Calling**: Agentic workflow with function calling
- 💬 **Modern UI**: Clean, dark-themed chat interface with streaming
- 📊 **Memory**: Persistent conversations with SQLite storage
- 🔍 **RAG Ready**: ChromaDB integration for document ingestion
- 🐳 **Docker Support**: Complete containerization with docker-compose
- ⚡ **Streaming**: Real-time response streaming via Server-Sent Events

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│                 │    │                 │    │                 │
│   Next.js UI    │◄──►│  FastAPI Server │◄──►│     Ollama      │
│   (Port 3000)   │    │   (Port 8080)   │    │  (Port 11434)   │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │                 │
                       │   SQLite DB     │
                       │   ChromaDB      │
                       │                 │
                       └─────────────────┘
```

## Quick Start

### Option 1: Docker Compose (Recommended)

1. **Clone and navigate:**
   ```bash
   git clone <your-repo>
   cd chatgpt-local
   ```

2. **Set environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env if needed
   ```

3. **Start all services:**
   ```bash
   docker-compose up -d
   ```

4. **Pull the model:**
   ```bash
   docker exec -it chatgpt-local-ollama-1 ollama pull gpt-oss:20b
   ```

5. **Open your browser:**
   Navigate to [http://localhost:3000](http://localhost:3000)

### Option 2: Manual Setup

#### Prerequisites

- Python 3.11+
- Node.js 20+
- Ollama installed and running

#### 1. Start Ollama

```bash
# Install Ollama (if not already installed)
# Visit: https://ollama.ai

# Start Ollama server
ollama serve

# Pull the model
ollama pull gpt-oss:20b
```

#### 2. Backend Setup

```bash
cd server

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp ../.env.example ../.env

# Start the server
python app.py
# or: uvicorn app:app --host 0.0.0.0 --port 8080 --reload
```

#### 3. Frontend Setup

```bash
cd ui

# Install pnpm (if not installed)
npm install -g pnpm

# Install dependencies
pnpm install

# Start development server
pnpm dev
```

#### 4. Access the Application

Open [http://localhost:3000](http://localhost:3000) in your browser.

## Usage

### Basic Chat

1. Type your message in the input box
2. Press Enter to send (Shift+Enter for new line)
3. Watch the AI respond with streaming text

### Web Browsing

1. Toggle the **"Browsing"** switch in the header
2. Ask questions that require current information
3. The AI will automatically search the web and cite sources

Example prompts:
- "What's the latest news about AI?"
- "Search for Python FastAPI tutorials"
- "Find the current weather in New York"

### Tool Usage

The AI has access to these tools when browsing is enabled:

- **`web_search`**: Search the web via DuckDuckGo
- **`web_read`**: Extract clean text from web pages
- **`web_fetch`**: Get raw HTML from URLs
- **`time_now`**: Get current date and time
- **`system_info`**: Get system information

### Model Selection

- Use the dropdown in the header to switch between available Ollama models
- Adjust temperature slider for response creativity (0.0 = focused, 2.0 = creative)

### Conversations

- Conversations are automatically saved
- Click on past conversations in the sidebar to continue them
- Use the trash icon to delete conversations
- Start new conversations with the "New Chat" button

## Configuration

### Environment Variables

```env
# Ollama Configuration
OLLAMA_URL=http://localhost:11434
MODEL_ID=gpt-oss:20b

# Server Configuration
SERVER_PORT=8080
UI_ORIGIN=http://localhost:3000
ALLOW_TOOLS=true

# Database
DATABASE_PATH=data/conversations.db

# RAG (Future feature)
CHROMADB_PATH=data/chromadb
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Tool Configuration
MAX_WEB_PAGES_PER_TURN=5
MAX_HTML_SIZE_MB=2
WEB_TIMEOUT_SECONDS=10

# Generation Settings
DEFAULT_TEMPERATURE=0.7
```

### Available Models

Any Ollama model can be used. Popular options:

```bash
# Install different models
ollama pull llama3.1:8b          # Smaller, faster
ollama pull llama3.1:70b         # Larger, more capable
ollama pull codellama:13b        # Code-focused
ollama pull mistral:7b           # Alternative option
ollama pull qwen2.5:7b           # Multilingual
```

## API Reference

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/healthz` | Health check |
| GET | `/models` | List available Ollama models |
| POST | `/chat` | Chat with streaming (SSE) |
| GET | `/ws` | WebSocket chat connection |
| GET | `/conversations` | List conversations |
| GET | `/conversations/{id}/messages` | Get conversation messages |
| DELETE | `/conversations/{id}` | Delete conversation |

### Chat Request Format

```json
{
  "messages": [
    {"role": "user", "content": "Hello!"}
  ],
  "conversation_id": "optional-uuid",
  "enable_browsing": true,
  "temperature": 0.7,
  "model": "gpt-oss:20b"
}
```

### Streaming Response Format

```
data: {"type": "token", "content": "Hello"}
data: {"type": "tool_call", "tool_name": "web_search", "arguments": {"query": "test"}}
data: {"type": "tool_result", "tool_name": "web_search", "result": {...}}
data: {"type": "done"}
```

## Development

### Project Structure

```
chatgpt-local/
├── server/                 # FastAPI backend
│   ├── agents/            # Core AI agent logic
│   │   ├── core.py        # Main agent orchestration
│   │   ├── tools.py       # Web browsing tools
│   │   ├── memory.py      # Conversation storage
│   │   ├── rag.py         # Document ingestion (future)
│   │   ├── schemas.py     # Pydantic models
│   │   ├── settings.py    # Configuration
│   │   └── util.py        # Utilities
│   ├── app.py             # FastAPI application
│   ├── requirements.txt   # Python dependencies
│   └── Dockerfile         # Server container
├── ui/                    # Next.js frontend
│   ├── app/               # App router pages
│   ├── components/        # React components
│   ├── lib/               # API client and utilities
│   ├── styles/            # CSS styles
│   ├── package.json       # Node dependencies
│   └── Dockerfile         # UI container
├── docker-compose.yml     # Multi-service orchestration
├── .env.example           # Environment template
└── README.md              # This file
```

### Adding New Tools

1. **Define the tool function** in `server/agents/tools.py`:

```python
class MyCustomTool(ToolExecutor):
    async def execute(self, param1: str, param2: int = 5) -> Dict[str, Any]:
        # Your tool logic here
        return {"success": True, "result": "data"}
```

2. **Add to the registry**:

```python
TOOL_REGISTRY = {
    # existing tools...
    "my_custom_tool": MyCustomTool,
}
```

3. **Add tool definition** in `server/agents/schemas.py`:

```python
TOOL_DEFINITIONS.append({
    "type": "function",
    "function": {
        "name": "my_custom_tool",
        "description": "Description of what it does",
        "parameters": {
            "type": "object",
            "properties": {
                "param1": {"type": "string", "description": "Parameter description"},
                "param2": {"type": "integer", "default": 5}
            },
            "required": ["param1"]
        }
    }
})
```

### Running Tests

```bash
# Backend tests
cd server
python -m pytest tests/

# Frontend tests
cd ui
pnpm test
```

### Development Mode

```bash
# Start backend with auto-reload
cd server
uvicorn app:app --reload

# Start frontend with hot reload
cd ui
pnpm dev
```

## Troubleshooting

### Common Issues

1. **Ollama connection failed**
   ```bash
   # Check if Ollama is running
   curl http://localhost:11434/api/tags
   
   # Start Ollama if not running
   ollama serve
   ```

2. **Model not found**
   ```bash
   # List available models
   ollama list
   
   # Pull the required model
   ollama pull gpt-oss:20b
   ```

3. **Port conflicts**
   - Server: Change `SERVER_PORT` in `.env`
   - UI: Change port in `package.json` scripts
   - Ollama: Use `OLLAMA_HOST` environment variable

4. **Memory issues**
   - Reduce model size (try `llama3.1:8b` instead of larger models)
   - Adjust `max_tokens` in requests
   - Monitor system resources

5. **Web browsing not working**
   - Check `ALLOW_TOOLS=true` in environment
   - Verify internet connection
   - Check firewall settings

### Logs

```bash
# Docker logs
docker-compose logs -f server
docker-compose logs -f ui
docker-compose logs -f ollama

# Direct logs
tail -f server/logs/app.log
```

### Performance Tuning

1. **Model Selection**: Smaller models = faster responses
2. **Temperature**: Lower values = more focused responses
3. **Max Tokens**: Limit response length for speed
4. **Tool Usage**: Disable browsing for simple chats
5. **Concurrent Requests**: Adjust based on hardware

## Future Enhancements

- [ ] **File Upload**: RAG document ingestion via UI
- [ ] **Multi-tab Browsing**: Enhanced web research
- [ ] **Export Features**: Save chats as Markdown/PDF
- [ ] **Custom Models**: Support for local fine-tuned models
- [ ] **Plugin System**: Easy tool extension framework
- [ ] **Voice Interface**: Speech-to-text and text-to-speech
- [ ] **Mobile App**: React Native companion
- [ ] **Team Features**: Shared conversations and workspaces

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Support

- **Issues**: [GitHub Issues](https://github.com/your-repo/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-repo/discussions)
- **Documentation**: This README and inline code comments

---

**Built with ❤️ using Ollama, FastAPI, and Next.js**
