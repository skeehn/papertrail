import os
import sys
import types
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("ALLOWED_HOSTS", '["testserver","localhost"]')

if "aiohttp" not in sys.modules:
    sys.modules["aiohttp"] = types.SimpleNamespace(ClientSession=None)

if "feedparser" not in sys.modules:
    sys.modules["feedparser"] = types.SimpleNamespace(
        parse=lambda *args, **kwargs: None
    )

from app.main import app  # noqa: E402
import app.database.neo4j_client as neo4j_client_module  # noqa: E402


def test_list_entities_uses_entity_response(monkeypatch):
    client = TestClient(app)

    stub_entities = [
        {
            "name": "Transformer",
            "type": "concept",
            "description": "Deep learning architecture",
            "confidence": 0.75,
            "paper_id": "arXiv:1234",
            "paper_title": "Attention is All You Need",
        }
    ]

    def fake_search(query: str, entity_type: str = None, limit: int = 20):
        return stub_entities

    monkeypatch.setattr(neo4j_client_module, "NEO4J_AVAILABLE", True)
    monkeypatch.setattr(
        neo4j_client_module.GraphOperations,
        "search_entities",
        staticmethod(fake_search),
    )
    monkeypatch.setattr(neo4j_client_module.neo4j_client, "_driver", object())

    response = client.get("/api/v1/entities", params={"search": "trans", "limit": 5})

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == len(stub_entities)
    assert payload["entities"][0]["name"] == "Transformer"
    assert payload["entities"][0]["type"] == "concept"
    assert payload["entities"][0]["paper_id"] == "arXiv:1234"
    assert payload["entities"][0]["confidence"] == pytest.approx(0.75)
    assert "paper_title" not in payload["entities"][0]
