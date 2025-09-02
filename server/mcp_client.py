#!/usr/bin/env python3
"""
MCP Client for connecting to external MCP servers

Allows our local agent to use tools from external MCP servers
by connecting to them and registering their tools in our tool registry.
"""

import asyncio
import json
import logging
import subprocess
import sys
from typing import Any, Dict, List, Optional
from agents.settings import settings

logger = logging.getLogger(__name__)

class MCPClient:
    """Client for connecting to external MCP servers"""
    
    def __init__(self):
        self.connected_servers = {}
        self.external_tools = {}
        
    async def connect_to_server(self, server_config: Dict[str, str]) -> bool:
        """Connect to an external MCP server"""
        try:
            name = server_config.get("name")
            command = server_config.get("command")
            
            if not name or not command:
                logger.error(f"Invalid server config: {server_config}")
                return False
            
            # For now, we'll create a simple registry
            # In a full implementation, this would establish actual connections
            self.connected_servers[name] = server_config
            logger.info(f"Registered MCP server: {name}")
            
            # Get tools from this server (simplified)
            tools = await self._get_server_tools(name, command)
            self.external_tools.update(tools)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to MCP server {server_config}: {e}")
            return False
    
    async def _get_server_tools(self, server_name: str, command: str) -> Dict[str, Dict]:
        """Get available tools from an MCP server"""
        # Simplified implementation - in practice this would use the MCP protocol
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
            
            # In a full implementation, this would make the actual MCP call
            logger.info(f"Would call {tool_name} on server {server_name} with {arguments}")
            return {"result": f"External tool {tool_name} called successfully"}
            
        except Exception as e:
            logger.error(f"External tool call failed for {tool_name}: {e}")
            return {"error": str(e)}
    
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
