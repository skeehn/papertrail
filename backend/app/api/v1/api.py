from fastapi import APIRouter

from app.api.v1.endpoints import (
    arxiv,
    chat_tools,
    citations,
    communities,
    contradictions,
    dashboard,
    entities,
    gaps,
    graph,
    insights,
    memories,
    papers,
    recommendations,
    search,
    settings,
    web_search,
)

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(papers.router, prefix="/papers", tags=["papers"])
api_router.include_router(entities.router, prefix="/entities", tags=["entities"])
api_router.include_router(chat_tools.router, prefix="/chat", tags=["chat"])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
api_router.include_router(graph.router, prefix="/graph", tags=["graph"])
api_router.include_router(memories.router, prefix="/memories", tags=["memories"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(web_search.router, prefix="/web-search", tags=["web-search"])
api_router.include_router(arxiv.router, prefix="/arxiv", tags=["arxiv"])
api_router.include_router(
    communities.router, prefix="/communities", tags=["communities"]
)
api_router.include_router(insights.router, prefix="/insights", tags=["insights"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(citations.router, prefix="/citations", tags=["citations"])
api_router.include_router(
    contradictions.router, prefix="/contradictions", tags=["contradictions"]
)
api_router.include_router(gaps.router, prefix="/gaps", tags=["gaps"])
api_router.include_router(
    recommendations.router, prefix="/recommendations", tags=["recommendations"]
)
