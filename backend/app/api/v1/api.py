from fastapi import APIRouter

from app.api.v1.endpoints import (
    agents,
    entities,
    graph,
    memories,
    papers,
    search,
    web_search,
)

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(papers.router, prefix="/papers", tags=["papers"])
api_router.include_router(entities.router, prefix="/entities", tags=["entities"])
api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
api_router.include_router(graph.router, prefix="/graph", tags=["graph"])
api_router.include_router(memories.router, prefix="/memories", tags=["memories"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(web_search.router, prefix="/web-search", tags=["web-search"])
