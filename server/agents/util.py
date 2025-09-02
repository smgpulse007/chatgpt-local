import json
from typing import Dict, Any, AsyncGenerator
import asyncio

def create_sse_data(data: Dict[str, Any]) -> str:
    """Create Server-Sent Events formatted data"""
    return f"data: {json.dumps(data)}\n\n"

def create_sse_event(event: str, data: Dict[str, Any]) -> str:
    """Create Server-Sent Events with event type"""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"

async def chunk_text(text: str, max_chunk_size: int = 1000) -> AsyncGenerator[str, None]:
    """Chunk text into smaller pieces for streaming"""
    for i in range(0, len(text), max_chunk_size):
        chunk = text[i:i + max_chunk_size]
        yield chunk
        await asyncio.sleep(0.01)  # Small delay for streaming effect

def count_tokens_estimate(text: str) -> int:
    """Rough estimate of token count (4 chars per token)"""
    return len(text) // 4

def truncate_text(text: str, max_tokens: int = 2000) -> str:
    """Truncate text to approximate token limit"""
    max_chars = max_tokens * 4
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "...[truncated]"

def format_tool_call(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Format tool call for LLM"""
    return {
        "type": "function",
        "function": {
            "name": tool_name,
            "arguments": json.dumps(arguments)
        }
    }

def parse_tool_calls(content: str) -> list[Dict[str, Any]]:
    """Parse tool calls from LLM response"""
    tool_calls = []
    
    # Look for JSON blocks that might contain tool calls
    try:
        # Try to find JSON-like patterns
        import re
        json_pattern = r'\{[^{}]*"tool_call"[^{}]*\}'
        matches = re.findall(json_pattern, content)
        
        for match in matches:
            try:
                data = json.loads(match)
                if "tool_call" in data:
                    tool_calls.append(data)
            except json.JSONDecodeError:
                continue
                
    except Exception:
        pass
    
    return tool_calls

def sanitize_url(url: str) -> str:
    """Basic URL sanitization"""
    url = url.strip()
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    return url

def extract_domain(url: str) -> str:
    """Extract domain from URL"""
    try:
        from urllib.parse import urlparse
        return urlparse(url).netloc
    except:
        return url

def is_valid_url(url: str) -> bool:
    """Check if URL is valid"""
    try:
        from urllib.parse import urlparse
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False
