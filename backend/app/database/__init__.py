"""Database module with HydraDB (graph + vector) support and fallback to mock store"""

from typing import Any, Dict, List, Optional

import structlog

from app.core.config import settings
from app.core.logging import get_logger
from app.database.mock_store import mock_store
from app.database.hydradb_store import hydradb_store
from app.database.neo4j_client import GraphOperations

logger = get_logger("database")

# For backward compatibility - helix_store is now hydradb_store
helix_store = hydradb_store

# Flag to track if HydraDB is connected
HYDRADB_CONNECTED = False


async def init_database() -> None:
    """Initialize database connections"""
    global HYDRADB_CONNECTED
    try:
        await hydradb_store.connect()
        HYDRADB_CONNECTED = True
        logger.info("Database initialized with HydraDB connection")
    except Exception as e:
        logger.warning(f"HydraDB connection failed, using mock store: {e}")
        HYDRADB_CONNECTED = False


async def close_database() -> None:
    """Close database connections"""
    global HYDRADB_CONNECTED
    if HYDRADB_CONNECTED:
        await hydradb_store.disconnect()
        HYDRADB_CONNECTED = False


# Async wrapper functions for HydraDB operations
async def get_paper_by_id_async(paper_id: str) -> Optional[Dict[str, Any]]:
    """Get paper by ID from HydraDB or mock store"""
    if HYDRADB_CONNECTED:
        try:
            return await hydradb_store.get_paper_by_id(paper_id)
        except Exception as e:
            logger.error(f"Failed to get paper from HydraDB: {e}")

    return mock_store.get_paper(paper_id)


async def list_papers_async(
    skip: int = 0, limit: int = 20, search: str = None
) -> List[Dict[str, Any]]:
    """List papers from HydraDB or mock store"""
    if HYDRADB_CONNECTED:
        try:
            return await hydradb_store.list_papers(skip=skip, limit=limit, search=search)
        except Exception as e:
            logger.error(f"Failed to list papers from HydraDB: {e}")

    return mock_store.list_papers(skip=skip, limit=limit, search=search)


async def delete_paper_async(paper_id: str) -> bool:
    """Delete a paper from HydraDB or mock store"""
    if HYDRADB_CONNECTED:
        try:
            return await hydradb_store.delete_paper(paper_id)
        except Exception as e:
            logger.error(f"Failed to delete paper from HydraDB: {e}")

    return mock_store.delete_paper(paper_id)


async def get_paper_entities_async(paper_id: str) -> List[Dict[str, Any]]:
    """Get entities for a paper from HydraDB or mock store"""
    if HYDRADB_CONNECTED:
        try:
            return await hydradb_store.get_paper_entities(paper_id)
        except Exception as e:
            logger.error(f"Failed to get entities from HydraDB: {e}")

    return mock_store.get_paper_entities(paper_id)


async def get_related_papers_async(paper_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Get related papers from HydraDB or mock store"""
    if HYDRADB_CONNECTED:
        try:
            return await hydradb_store.get_related_papers(paper_id, limit=limit)
        except Exception as e:
            logger.error(f"Failed to get related papers from HydraDB: {e}")

    return mock_store.get_related_papers(paper_id, limit=limit)


async def store_paper_async(paper_data: dict) -> str:
    """Store a paper to HydraDB or mock store"""
    paper_id = paper_data.get("arxiv_id") or paper_data.get("id")

    if HYDRADB_CONNECTED and paper_id:
        try:
            return await hydradb_store.store_paper(paper_data)
        except Exception as e:
            logger.error(f"Failed to store paper to HydraDB: {e}")

    return mock_store.store_paper(paper_data)


async def store_entities_async(paper_id: str, entities: list):
    """Store entities to HydraDB or mock store"""
    if HYDRADB_CONNECTED:
        try:
            return await hydradb_store.store_entities(paper_id, entities)
        except Exception as e:
            logger.error(f"Failed to store entities to HydraDB: {e}")

    mock_store.store_entities(paper_id, entities)


async def store_relationships_async(paper_id: str, relationships: list):
    """Store relationships to HydraDB or mock store"""
    if HYDRADB_CONNECTED:
        try:
            return await hydradb_store.store_relationships(paper_id, relationships)
        except Exception as e:
            logger.error(f"Failed to store relationships to HydraDB: {e}")

    mock_store.store_relationships(paper_id, relationships)


async def get_graph_statistics_async() -> Dict[str, Any]:
    """Get graph statistics from HydraDB or mock store"""
    if HYDRADB_CONNECTED:
        try:
            return await hydradb_store.get_graph_statistics()
        except Exception as e:
            logger.error(f"Failed to get graph stats from HydraDB: {e}")

    # Fall back to mock
    return {
        "node_count": len(mock_store.entities) + len(mock_store.papers),
        "relationship_count": len(mock_store.relationships),
        "node_types": {
            "Memory": len([k for k in mock_store.memories]),
            "Paper": len(mock_store.papers),
            "Entity": len(mock_store.entities),
            "Concept": len(set(e.get("type") for e in mock_store.entities.values())),
        },
        "relationship_types": {
            "MENTIONS": len(mock_store.entities) * 2,
            "RELATES_TO": len(mock_store.relationships),
            "AUTHORED_BY": len(mock_store.papers) * 2,
            "CITES": len(mock_store.papers),
        },
        "source": "mock_store",
    }


# Synchronous wrappers for backward compatibility (run in thread pool if needed)
def get_paper_by_id(paper_id: str) -> Optional[Dict[str, Any]]:
    """Get paper by ID from HydraDB or mock store (sync)"""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # We're in an async context, create a task
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, get_paper_by_id_async(paper_id))
                return future.result()
        else:
            return asyncio.run(get_paper_by_id_async(paper_id))
    except RuntimeError:
        return asyncio.run(get_paper_by_id_async(paper_id))


def list_papers(
    skip: int = 0, limit: int = 20, search: str = None
) -> List[Dict[str, Any]]:
    """List papers from HydraDB or mock store (sync)"""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, list_papers_async(skip=skip, limit=limit, search=search))
                return future.result()
        else:
            return asyncio.run(list_papers_async(skip=skip, limit=limit, search=search))
    except RuntimeError:
        return asyncio.run(list_papers_async(skip=skip, limit=limit, search=search))


def delete_paper(paper_id: str) -> bool:
    """Delete a paper from HydraDB or mock store (sync)"""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, delete_paper_async(paper_id))
                return future.result()
        else:
            return asyncio.run(delete_paper_async(paper_id))
    except RuntimeError:
        return asyncio.run(delete_paper_async(paper_id))


def get_paper_entities(paper_id: str) -> List[Dict[str, Any]]:
    """Get entities for a paper from HydraDB or mock store (sync)"""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, get_paper_entities_async(paper_id))
                return future.result()
        else:
            return asyncio.run(get_paper_entities_async(paper_id))
    except RuntimeError:
        return asyncio.run(get_paper_entities_async(paper_id))


def get_related_papers(paper_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Get related papers from HydraDB or mock store (sync)"""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, get_related_papers_async(paper_id, limit=limit))
                return future.result()
        else:
            return asyncio.run(get_related_papers_async(paper_id, limit=limit))
    except RuntimeError:
        return asyncio.run(get_related_papers_async(paper_id, limit=limit))


def store_paper(paper_data: dict) -> str:
    """Store a paper to HydraDB or mock store (sync)"""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, store_paper_async(paper_data))
                return future.result()
        else:
            return asyncio.run(store_paper_async(paper_data))
    except RuntimeError:
        return asyncio.run(store_paper_async(paper_data))


def store_entities(paper_id: str, entities: list):
    """Store entities to HydraDB or mock store (sync)"""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, store_entities_async(paper_id, entities))
                return future.result()
        else:
            return asyncio.run(store_entities_async(paper_id, entities))
    except RuntimeError:
        return asyncio.run(store_entities_async(paper_id, entities))


def store_relationships(paper_id: str, relationships: list):
    """Store relationships to HydraDB or mock store (sync)"""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, store_relationships_async(paper_id, relationships))
                return future.result()
        else:
            return asyncio.run(store_relationships_async(paper_id, relationships))
    except RuntimeError:
        return asyncio.run(store_relationships_async(paper_id, relationships))


def get_graph_statistics() -> Dict[str, Any]:
    """Get graph statistics from HydraDB or mock store (sync)"""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, get_graph_statistics_async())
                return future.result()
        else:
            return asyncio.run(get_graph_statistics_async())
    except RuntimeError:
        return asyncio.run(get_graph_statistics_async())