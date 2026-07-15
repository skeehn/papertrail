"""Settings endpoints: manage API keys and report service status.

Lets a fresh clone be configured entirely from the UI — add an LLM key and the
chat works. Pinecone/Neo4j stay optional; status shows what each unlocks.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core import user_config
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger("settings")


class KeysRequest(BaseModel):
    """Any subset of managed keys. Empty string clears a key."""

    OPENAI_API_KEY: Optional[str] = Field(default=None)
    OPENAI_BASE_URL: Optional[str] = Field(default=None)
    OPENAI_MODEL: Optional[str] = Field(default=None)
    PINECONE_API_KEY: Optional[str] = Field(default=None)
    PINECONE_INDEX_NAME: Optional[str] = Field(default=None)
    PINECONE_HOST: Optional[str] = Field(default=None)
    NEO4J_URI: Optional[str] = Field(default=None)
    NEO4J_USERNAME: Optional[str] = Field(default=None)
    NEO4J_PASSWORD: Optional[str] = Field(default=None)


@router.get("/keys")
async def get_keys() -> Dict[str, Any]:
    """Masked view of configured keys (secrets never returned)."""
    return {"keys": user_config.masked_status(), "path": str(user_config.CONFIG_PATH)}


@router.post("/keys")
async def set_keys(request: KeysRequest) -> Dict[str, Any]:
    """Persist keys to the user config file, then re-check services."""
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    user_config.save_keys(updates)
    return {
        "ok": True,
        "keys": user_config.masked_status(),
        "services": await _service_status(),
    }


@router.get("/status")
async def get_status() -> Dict[str, Any]:
    """What is configured and what each service unlocks."""
    return {"services": await _service_status(), "keys": user_config.masked_status()}


async def _service_status() -> Dict[str, Any]:
    """Live status per service. Everything except the LLM is optional."""
    llm_key = user_config.get_key("OPENAI_API_KEY")
    llm_ready = bool(llm_key) and not llm_key.startswith("sk-placeholder")

    pinecone_ready = False
    try:
        from app.services.pinecone_store import pinecone_store

        pinecone_ready = bool(pinecone_store.is_connected)
    except Exception:  # noqa: BLE001
        pinecone_ready = False

    neo4j_ready = False
    try:
        from app.database import NEO4J_CONNECTED

        neo4j_ready = bool(NEO4J_CONNECTED)
    except Exception:  # noqa: BLE001
        neo4j_ready = False

    return {
        "llm": {
            "configured": llm_ready,
            "required": True,
            "label": "Chat model",
            "unlocks": "Chat. Without a key the chat cannot answer.",
        },
        "pinecone": {
            "configured": pinecone_ready,
            "required": False,
            "label": "Pinecone",
            "unlocks": "Semantic search. Without it, paper search falls back to keywords.",
        },
        "neo4j": {
            "configured": neo4j_ready,
            "required": False,
            "label": "Neo4j",
            "unlocks": "Knowledge graph + paper library. Without it, the graph is empty.",
        },
    }
