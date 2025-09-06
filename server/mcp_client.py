#!/usr/bin/env python3
"""
MCP Client for connecting to external MCP servers

Allows our local agent to use tools from external MCP servers
by connecting to them and registering their tools in our tool registry.
"""

import asyncio
import json
import logging
import sys
import shlex
from typing import Any, Dict, List, Optional
from agents.settings import settings

logger = logging.getLogger(__name__)

class MCPClient:
    """Client for connecting to external MCP servers"""
    
    def __init__(self):
        self.connected_servers: Dict[str, Dict[str, Any]] = {}
        self.external_tools: Dict[str, Dict[str, Any]] = {}
        
    async def connect_to_server(self, server_config: Dict[str, str]) -> bool:
        """Connect to an external MCP server"""
        try:
            name = server_config.get("name")
            command = server_config.get("command")
            host = server_config.get("host")
            port = server_config.get("port")

            if not name:
                logger.error(f"Invalid server config: {server_config}")
                return False

            reader: Optional[asyncio.StreamReader] = None
            writer: Optional[asyncio.StreamWriter] = None
            process: Optional[asyncio.subprocess.Process] = None

            if command:
                process = await asyncio.create_subprocess_exec(
                    *shlex.split(command),
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                )
                reader = process.stdout
                writer = process.stdin
            elif host and port:
                reader, writer = await asyncio.open_connection(host, int(port))
            else:
                logger.error(f"Invalid server config: {server_config}")
                return False

            self.connected_servers[name] = {
                "process": process,
                "reader": reader,
                "writer": writer,
            }
            logger.info(f"Connected to MCP server: {name}")

            tools = await self._get_server_tools(name)
            self.external_tools[name] = tools

            return True

        except Exception as e:
            logger.error(f"Failed to connect to MCP server {server_config}: {e}")
            return False
    
    async def _get_server_tools(self, server_name: str) -> Dict[str, Dict]:
        """Get available tools from an MCP server"""
        try:
            server = self.connected_servers.get(server_name)
            if not server:
                return {}

            reader: asyncio.StreamReader = server["reader"]
            writer: asyncio.StreamWriter = server["writer"]

            request = {"method": "tools/list"}
            writer.write(json.dumps(request).encode() + b"\n")
            await writer.drain()

            line = await reader.readline()
            if not line:
                return {}

            response = json.loads(line.decode())
            tools_info = response.get("tools", [])
            tools: Dict[str, Dict[str, Any]] = {}

            for tool in tools_info:
                if "function" in tool:
                    fn = tool["function"]
                    tools[fn["name"]] = tool
                else:
                    name = tool.get("name")
                    tools[name] = {
                        "type": "function",
                        "function": {
                            "name": name,
                            "description": tool.get("description", ""),
                            "parameters": {
                                "type": "object",
                                "properties": {},
                            },
                        },
                    }

            return tools

        except Exception as e:
            logger.error(f"Failed to get tools from {server_name}: {e}")
            return {}
    
    async def call_external_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on an external MCP server"""
        try:
            # Find which server has this tool
            server_name = None
            for name, tools in self.external_tools.items():
                if tool_name in tools:
                    server_name = name
                    break
            
            if not server_name:
                return {"error": f"Tool {tool_name} not found in any connected server"}
            
            server = self.connected_servers.get(server_name)
            if not server:
                return {"error": f"Server {server_name} not connected"}

            reader: asyncio.StreamReader = server["reader"]
            writer: asyncio.StreamWriter = server["writer"]

            request = {
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments,
                },
            }

            writer.write(json.dumps(request).encode() + b"\n")
            await writer.drain()

            line = await reader.readline()
            if not line:
                return {"error": "No response from server"}

            response = json.loads(line.decode())
            return response
            
        except Exception as e:
            logger.error(f"External tool call failed for {tool_name}: {e}")
            return {"error": str(e)}

    async def disconnect_server(self, server_name: str) -> None:
        """Disconnect from a specific MCP server"""
        server = self.connected_servers.pop(server_name, None)
        if not server:
            return

        writer: Optional[asyncio.StreamWriter] = server.get("writer")
        if writer:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass

        process: Optional[asyncio.subprocess.Process] = server.get("process")
        if process:
            process.terminate()
            try:
                await process.wait()
            except ProcessLookupError:
                pass
    
    def get_available_external_tools(self) -> List[str]:
        """Get list of all available external tools"""
        tools = []
        for server_tools in self.external_tools.values():
            tools.extend(server_tools.keys())
        return tools
    
    async def initialize_from_config(self):
        """Initialize MCP connections from environment configuration"""
        mcp_endpoints = getattr(settings, 'mcp_endpoints', None)
        if not mcp_endpoints:
            logger.info("No MCP endpoints configured")
            return
        
        # Parse MCP_ENDPOINTS from environment
        # Format: "server1:command1,server2:command2"
        try:
            endpoints = mcp_endpoints.split(',')
            for endpoint in endpoints:
                if ':' in endpoint:
                    name, command = endpoint.split(':', 1)
                    server_config = {"name": name.strip(), "command": command.strip()}
                    await self.connect_to_server(server_config)
        except Exception as e:
            logger.error(f"Failed to parse MCP endpoints: {e}")

# Global MCP client instance
mcp_client = MCPClient()

async def initialize_mcp_client():
    """Initialize the global MCP client"""
    await mcp_client.initialize_from_config()

def get_mcp_client() -> MCPClient:
    """Get the global MCP client instance"""
    return mcp_client
