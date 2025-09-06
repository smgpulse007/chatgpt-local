from __future__ import annotations

"""Agent manager module."""

from typing import Dict, List, Optional
import uuid

from .core import Agent


class AgentManager:
    """Manage multiple :class:`Agent` instances keyed by agent IDs."""

    def __init__(self) -> None:
        self._agents: Dict[str, Agent] = {}

    def create_agent(self) -> str:
        """Create a new agent and return its identifier."""
        agent_id = str(uuid.uuid4())
        agent = Agent()
        self._agents[agent_id] = agent
        return agent_id

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Retrieve an existing agent by ID."""
        return self._agents.get(agent_id)

    def list_agents(self) -> List[str]:
        """Return list of active agent IDs."""
        return list(self._agents.keys())

    async def remove_agent(self, agent_id: str) -> bool:
        """Remove an agent by ID and close its resources.

        Returns ``True`` if the agent was removed, ``False`` otherwise.
        """
        agent = self._agents.pop(agent_id, None)
        if not agent:
            return False
        try:
            await agent.http_client.aclose()
        except Exception:
            # Ignore errors during cleanup
            pass
        return True
