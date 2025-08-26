from datetime import datetime
from typing import List, Optional

import structlog
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.logging import get_logger
from app.database.mock_store import mock_store

router = APIRouter()
logger = get_logger("memories")


class MemoryCreate(BaseModel):
    content: str
    memory_type: str = "episodic"
    metadata: Optional[dict] = None


class MemoryResponse(BaseModel):
    id: str
    content: str
    memory_type: str
    metadata: dict
    created_at: str


@router.get("/", response_model=List[MemoryResponse])
async def get_memories(
    limit: int = Query(20, ge=1, le=100),
    skip: int = Query(0, ge=0),
    memory_type: Optional[str] = None,
):
    """Get memories from the knowledge base"""
    try:
        # Get memories from mock store
        all_memories = mock_store.get_memories()

        # Filter by type if specified
        if memory_type:
            all_memories = [
                m for m in all_memories if m.get("memory_type") == memory_type
            ]

        # Apply pagination
        memories = all_memories[skip : skip + limit]

        logger.info("Retrieved memories", count=len(memories), total=len(all_memories))
        return memories

    except Exception as e:
        logger.error("Failed to get memories", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve memories")


@router.post("/", response_model=MemoryResponse)
async def create_memory(memory: MemoryCreate):
    """Create a new memory"""
    try:
        memory_data = {
            "content": memory.content,
            "memory_type": memory.memory_type,
            "metadata": memory.metadata or {},
            "created_at": datetime.utcnow().isoformat(),
        }

        memory_id = mock_store.store_memory(memory_data)
        stored_memory = mock_store.get_memory(memory_id)

        logger.info("Created memory", memory_id=memory_id, type=memory.memory_type)
        return stored_memory

    except Exception as e:
        logger.error("Failed to create memory", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create memory")


@router.get("/{memory_id}", response_model=MemoryResponse)
async def get_memory(memory_id: str):
    """Get a specific memory by ID"""
    try:
        memory = mock_store.get_memory(memory_id)
        if not memory:
            raise HTTPException(status_code=404, detail="Memory not found")

        return memory

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get memory", memory_id=memory_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve memory")
