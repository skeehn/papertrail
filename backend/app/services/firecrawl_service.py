"""Firecrawl service for web scraping and search"""

from typing import Any, Dict, List, Optional

try:
    from firecrawl import Firecrawl

    FIRECRAWL_AVAILABLE = True
except ImportError:
    Firecrawl = None
    FIRECRAWL_AVAILABLE = False

from app.core.config import settings
from app.core.logging import get_logger


class FirecrawlService:
    """Service for web scraping and search using Firecrawl"""

    def __init__(self):
        self.logger = get_logger("firecrawl")
        self.app = None

        if not FIRECRAWL_AVAILABLE:
            self.logger.warning("Firecrawl library not available")
        elif not settings.FIRECRAWL_API_KEY:
            self.logger.warning("Firecrawl API key not configured")
        else:
            self._init_client()

    def _init_client(self):
        """Initialize Firecrawl client"""
        try:
            self.app = Firecrawl(api_key=settings.FIRECRAWL_API_KEY)
            self.logger.info("Firecrawl client initialized")
        except Exception as e:
            self.logger.error("Failed to initialize Firecrawl", error=str(e))
            self.app = None

    def scrape_url(
        self, url: str, formats: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Scrape a single URL

        Args:
            url: URL to scrape
            formats: List of desired formats (e.g., ['markdown', 'html', 'screenshot'])

        Returns:
            Scraped content dictionary or None if failed
        """
        if not self.app:
            self.logger.error("Firecrawl client not initialized")
            return None

        try:
            # Default to markdown format
            if not formats:
                formats = ["markdown"]

            result = self.app.scrape(url, formats=formats)

            self.logger.info("URL scraped successfully", url=url)
            return result

        except Exception as e:
            self.logger.error("Failed to scrape URL", url=url, error=str(e))
            return None

    def scrape_paper_url(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Scrape a research paper URL (e.g., arXiv, ACL, etc.)

        Args:
            url: Paper URL

        Returns:
            Scraped paper content with metadata
        """
        result = self.scrape_url(url, formats=["markdown"])

        if not result:
            return None

        # Extract content
        content = result.get("markdown", result.get("content", ""))

        return {"url": url, "content": content, "metadata": result.get("metadata", {})}

    def search_web(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search the web using Firecrawl

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of search results
        """
        if not self.app:
            self.logger.error("Firecrawl client not initialized")
            return []

        try:
            results = self.app.search(query, limit=limit)

            self.logger.info("Web search completed", query=query, results=len(results))
            return results

        except Exception as e:
            self.logger.error("Web search failed", query=query, error=str(e))
            return []

    def search_research_papers(
        self, query: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for research papers on the web

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of paper results
        """
        # Enhance query for research papers
        enhanced_query = f"{query} research paper PDF site:arxiv.org OR site:aclweb.org OR site:openreview.net"

        return self.search_web(enhanced_query, limit)

    def crawl_website(
        self, url: str, max_depth: int = 2, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Crawl a website starting from a URL

        Args:
            url: Starting URL
            max_depth: Maximum depth to crawl
            limit: Maximum number of pages to crawl

        Returns:
            List of crawled pages
        """
        if not self.app:
            self.logger.error("Firecrawl client not initialized")
            return []

        try:
            result = self.app.crawl(url, max_depth=max_depth, limit=limit)

            pages = result.get("data", [])

            self.logger.info("Website crawled", url=url, pages=len(pages))
            return pages

        except Exception as e:
            self.logger.error("Crawl failed", url=url, error=str(e))
            return []

    def map_website(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Map a website's structure

        Args:
            url: Website URL

        Returns:
            Website map data
        """
        if not self.app:
            self.logger.error("Firecrawl client not initialized")
            return None

        try:
            result = self.app.map(url)

            self.logger.info("Website mapped", url=url)
            return result

        except Exception as e:
            self.logger.error("Map failed", url=url, error=str(e))
            return None

    def extract_paper_metadata_from_url(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Extract paper metadata from a URL

        Args:
            url: Paper URL

        Returns:
            Paper metadata dictionary
        """
        content = self.scrape_paper_url(url)

        if not content:
            return None

        # Try to extract metadata from content
        # This is a simple implementation - could be enhanced with LLM
        text = content.get("content", "")
        metadata = content.get("metadata", {})

        # Extract title from metadata or content
        title = metadata.get("title", "")
        if not title and text:
            # Try to find title in first few lines
            lines = text.split("\n")
            for line in lines[:10]:
                if len(line) > 20 and len(line) < 200:
                    title = line.strip("#").strip()
                    break

        return {
            "url": url,
            "title": title,
            "content": text[:5000],  # First 5000 chars
            "full_content": text,
            "metadata": metadata,
        }


# Global Firecrawl service instance
firecrawl_service = FirecrawlService()


def scrape_url(url: str) -> Optional[Dict[str, Any]]:
    """Scrape a URL"""
    return firecrawl_service.scrape_url(url)


def search_web(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Search the web"""
    return firecrawl_service.search_web(query, limit)


def search_research_papers_web(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Search for research papers"""
    return firecrawl_service.search_research_papers(query, limit)


def crawl_website(url: str, max_depth: int = 2) -> List[Dict[str, Any]]:
    """Crawl a website"""
    return firecrawl_service.crawl_website(url, max_depth)
