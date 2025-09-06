import asyncio
import sys
from pathlib import Path

# Ensure repository root is on sys.path for imports
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "server"))

from server.mcp_client import MCPClient


async def run_client():
    client = MCPClient()
    server_config = {"name": "local", "command": "python server/mcp_server.py"}
    try:
        connected = await client.connect_to_server(server_config)
        assert connected
        assert "time.now" in client.get_available_external_tools()
        response = await client.call_external_tool("time.now", {})
        assert "result" in response
        assert response["result"]["success"]
    finally:
        await client.disconnect_server("local")


def test_round_trip_tool_call():
    asyncio.run(run_client())
