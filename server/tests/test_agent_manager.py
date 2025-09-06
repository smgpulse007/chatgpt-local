import json
import sys
import importlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Create a TestClient with isolated temp directory and database."""
    server_dir = Path(__file__).resolve().parents[1]
    sys.path.append(str(server_dir))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "conversations.db"))
    app_module = importlib.reload(importlib.import_module("app"))
    with TestClient(app_module.app) as client:
        yield client


def test_agent_creation_and_listing(client):
    resp = client.post("/agents")
    assert resp.status_code == 200
    agent_id = resp.json()["agent_id"]

    resp = client.get("/agents")
    assert resp.status_code == 200
    assert agent_id in resp.json()["agents"]


def test_message_routing_and_teardown(client, monkeypatch):
    from agents.core import Agent
    app_module = importlib.import_module("app")

    agent_id1 = client.post("/agents").json()["agent_id"]
    agent_id2 = client.post("/agents").json()["agent_id"]

    agent1 = app_module.agent_manager.get_agent(agent_id1)
    agent2 = app_module.agent_manager.get_agent(agent_id2)
    token_map = {agent1: agent_id1, agent2: agent_id2}

    async def fake_run_streaming(self, *args, **kwargs):
        yield {"type": "token", "content": token_map[self]}
        return

    monkeypatch.setattr(Agent, "run_streaming", fake_run_streaming)

    payload = {"messages": [{"role": "user", "content": "hi"}], "agent_id": agent_id1}
    resp1 = client.post("/chat", json=payload)
    assert agent_id1 in resp1.text

    payload["agent_id"] = agent_id2
    resp2 = client.post("/chat", json=payload)
    assert agent_id2 in resp2.text

    # delete first agent and ensure further chat fails
    del_resp = client.delete(f"/agents/{agent_id1}")
    assert del_resp.status_code == 200

    resp_deleted = client.post(
        "/chat",
        json={"messages": [{"role": "user", "content": "hi"}], "agent_id": agent_id1},
    )
    assert resp_deleted.status_code == 404


def test_websocket_routing(client, monkeypatch):
    from agents.core import Agent
    app_module = importlib.import_module("app")

    agent_id = client.post("/agents").json()["agent_id"]
    agent = app_module.agent_manager.get_agent(agent_id)
    token_map = {agent: agent_id}

    async def fake_run_streaming(self, *args, **kwargs):
        yield {"type": "token", "content": token_map[self]}
        return

    monkeypatch.setattr(Agent, "run_streaming", fake_run_streaming)

    with client.websocket_connect("/ws") as ws:
        message = {"messages": [{"role": "user", "content": "hi"}], "agent_id": agent_id}
        ws.send_text(json.dumps(message))
        response = json.loads(ws.receive_text())
        assert response["content"] == agent_id
        done = json.loads(ws.receive_text())
        assert done["type"] == "done"
