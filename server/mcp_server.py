#!/usr/bin/env python3
"""
MCP Server for Local ChatGPT Tools

Exposes local tools via Model Context Protocol:
- web.search: Search the web via DuckDuckGo
- web.read: Read and extract clean text from a webpage
- web.fetch: Get raw HTML from a URL
- time.now: Get current date and time
- system.info: Get system information
- rag.search: Search RAG database (optional)
"""

import asyncio
import json
import logging
import sys
from typing import Any, Dict, List, Optional

# Note: MCP SDK may not be available yet, so we'll create a basic implementation
# that follows the MCP protocol specification

from agents.tools import (
    WebSearchTool, WebReadTool, WebFetchTool, 
    TimeNowTool, SystemInfoTool
)

logger = logging.getLogger(__name__)

class MCPServer:
    """Basic MCP Server implementation"""
    
    def __init__(self):
        self.tools = {
            "web.search": WebSearchTool(),
            "web.read": WebReadTool(),
            "web.fetch": WebFetchTool(),
            "time.now": TimeNowTool(),
            "system.info": SystemInfoTool(),
        }
        
    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Get OpenAI-style tool schemas for all tools"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "web.search",
                    "description": "Search the web for recent info via DuckDuckGo",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"},
                            "max_results": {"type": "integer", "minimum": 1, "maximum": 10, "default": 5}
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "web.read",
                    "description": "Read and extract clean text from a webpage",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "string", "description": "URL to read"}
                        },
                        "required": ["url"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "web.fetch",
                    "description": "Get raw HTML from a URL",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "string", "description": "URL to fetch"}
                        },
                        "required": ["url"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "time.now",
                    "description": "Get current date and time",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "system.info",
                    "description": "Get system information",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            }
        ]
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool and return the result"""
        if name not in self.tools:
            return {"error": f"Unknown tool: {name}"}
        
        try:
            tool = self.tools[name]
            
            # Map MCP names to tool methods
            if name == "web.search":
                result = await tool.execute(**arguments)
            elif name == "web.read":
                result = await tool.execute(**arguments)
            elif name == "web.fetch":
                result = await tool.execute(**arguments)
            elif name == "time.now":
                result = await tool.execute()
            elif name == "system.info":
                result = await tool.execute()
            else:
                return {"error": f"Tool {name} not implemented"}
            
            return {"result": result}
            
        except Exception as e:
            logger.error(f"Tool execution error for {name}: {e}")
            return {"error": str(e)}
    
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP request"""
        method = request.get("method")
        params = request.get("params", {})
        
        if method == "tools/list":
            return {
                "tools": [
                    {"name": name, "description": schema["function"]["description"]}
                    for name, schema in zip(self.tools.keys(), self.get_tool_schemas())
                ]
            }
        elif method == "tools/call":
            name = params.get("name")
            arguments = params.get("arguments", {})
            return await self.call_tool(name, arguments)
        else:
            return {"error": f"Unknown method: {method}"}

async def main():
    """Run MCP server"""
    server = MCPServer()
    
    # Simple stdio-based protocol
    while True:
        try:
            line = input()
            if not line:
                break
                
            request = json.loads(line)
            response = await server.handle_request(request)
            print(json.dumps(response))
            
        except EOFError:
            break
        except Exception as e:
            error_response = {"error": str(e)}
            print(json.dumps(error_response))

if __name__ == "__main__":
    asyncio.run(main())
