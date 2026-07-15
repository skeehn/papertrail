"""ArXiv API client for fetching and downloading research papers"""

import os
import re
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

try:
    import arxiv

    ARXIV_AVAILABLE = True
except ImportError:
    arxiv = None
    ARXIV_AVAILABLE = False

from app.core.config import settings
from app.core.logging import get_logger


class ArXivClient:
    """Client for interacting with arXiv API"""

    def __init__(self):
        """Initialize ArXiv client"""
        self.logger = get_logger("arxiv_client")
        self.download_dir = settings.ARXIV_DOWNLOAD_DIR
        self.rate_limit = settings.ARXIV_RATE_LIMIT
        self.max_results = settings.ARXIV_MAX_RESULTS
        self.last_request_time = 0

        # arxiv >= 2.0 fetches results via a Client, not Search.results()
        self._client = arxiv.Client() if ARXIV_AVAILABLE else None

        # Ensure download directory exists
        os.makedirs(self.download_dir, exist_ok=True)

        if not ARXIV_AVAILABLE:
            self.logger.warning("ArXiv library not installed - ArXiv features disabled")

    def _rate_limit_wait(self):
        """Enforce rate limiting between requests"""
        if self.rate_limit > 0:
            time_since_last = time.time() - self.last_request_time
            wait_time = (1.0 / self.rate_limit) - time_since_last
            if wait_time > 0:
                time.sleep(wait_time)
        self.last_request_time = time.time()

    def search_papers(
        self,
        query: str,
        max_results: int = 10,
        sort_by: str = "relevance",
        sort_order: str = "descending",
        categories: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for papers on arXiv

        Args:
            query: Search query string
            max_results: Maximum number of results to return
            sort_by: Sort criterion (relevance, lastUpdatedDate, submittedDate)
            sort_order: Sort order (ascending, descending)
            categories: List of arXiv categories to filter by (e.g., ['cs.AI', 'cs.LG'])

        Returns:
            List of paper metadata dictionaries
        """
        self._rate_limit_wait()

        try:
            # Add category filter to query if specified
            search_query = query
            if categories:
                category_filter = " OR ".join([f"cat:{cat}" for cat in categories])
                search_query = f"({query}) AND ({category_filter})"

            # Map sort_by to arxiv.SortCriterion
            sort_criterion_map = {
                "relevance": arxiv.SortCriterion.Relevance,
                "lastUpdatedDate": arxiv.SortCriterion.LastUpdatedDate,
                "submittedDate": arxiv.SortCriterion.SubmittedDate,
            }
            sort_criterion = sort_criterion_map.get(
                sort_by, arxiv.SortCriterion.Relevance
            )

            # Map sort_order to arxiv.SortOrder
            sort_order_map = {
                "ascending": arxiv.SortOrder.Ascending,
                "descending": arxiv.SortOrder.Descending,
            }
            order = sort_order_map.get(sort_order, arxiv.SortOrder.Descending)

            # Create search
            search = arxiv.Search(
                query=search_query,
                max_results=min(max_results, self.max_results),
                sort_by=sort_criterion,
                sort_order=order,
            )

            # Execute search and collect results
            papers = []
            for result in self._client.results(search):
                paper = self._parse_paper_result(result)
                papers.append(paper)

            self.logger.info("ArXiv search completed", query=query, results=len(papers))
            return papers

        except Exception as e:
            self.logger.error("ArXiv search failed", query=query, error=str(e))
            return []

    def get_paper_by_id(self, arxiv_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific paper by its arXiv ID

        Args:
            arxiv_id: arXiv ID (e.g., '2301.00001' or 'arXiv:2301.00001')

        Returns:
            Paper metadata dictionary or None if not found
        """
        self._rate_limit_wait()

        try:
            # Clean arXiv ID
            clean_id = arxiv_id.replace("arXiv:", "").strip()

            # Search by ID
            search = arxiv.Search(id_list=[clean_id])
            result = next(self._client.results(search), None)

            if result:
                paper = self._parse_paper_result(result)
                self.logger.info("Paper fetched", arxiv_id=clean_id)
                return paper
            else:
                self.logger.warning("Paper not found", arxiv_id=clean_id)
                return None

        except Exception as e:
            self.logger.error("Failed to fetch paper", arxiv_id=arxiv_id, error=str(e))
            return None

    def get_papers_by_ids(self, arxiv_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Get multiple papers by their arXiv IDs

        Args:
            arxiv_ids: List of arXiv IDs

        Returns:
            List of paper metadata dictionaries
        """
        self._rate_limit_wait()

        try:
            # Clean IDs
            clean_ids = [id.replace("arXiv:", "").strip() for id in arxiv_ids]

            # Search by IDs
            search = arxiv.Search(id_list=clean_ids)

            papers = []
            for result in self._client.results(search):
                paper = self._parse_paper_result(result)
                papers.append(paper)

            self.logger.info("Papers fetched", count=len(papers))
            return papers

        except Exception as e:
            self.logger.error("Failed to fetch papers", error=str(e))
            return []

    def download_paper(
        self, arxiv_id: str, filename: Optional[str] = None
    ) -> Optional[str]:
        """
        Download PDF for a paper

        Args:
            arxiv_id: arXiv ID
            filename: Optional filename (defaults to arxiv_id.pdf)

        Returns:
            Path to downloaded PDF or None if failed
        """
        self._rate_limit_wait()

        try:
            # Clean arXiv ID
            clean_id = arxiv_id.replace("arXiv:", "").strip()

            # Get paper metadata
            search = arxiv.Search(id_list=[clean_id])
            paper = next(self._client.results(search), None)

            if not paper:
                self.logger.error("Paper not found for download", arxiv_id=clean_id)
                return None

            # Determine filename
            if not filename:
                # Sanitize ID for filename
                safe_id = clean_id.replace("/", "_").replace(":", "_")
                filename = f"{safe_id}.pdf"

            filepath = os.path.join(self.download_dir, filename)

            # Download PDF
            paper.download_pdf(dirpath=self.download_dir, filename=filename)

            self.logger.info("Paper downloaded", arxiv_id=clean_id, path=filepath)
            return filepath

        except Exception as e:
            self.logger.error(
                "Failed to download paper", arxiv_id=arxiv_id, error=str(e)
            )
            return None

    def search_by_category(
        self, category: str, max_results: int = 50, start_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for recent papers in a specific category

        Args:
            category: arXiv category (e.g., 'cs.AI', 'cs.LG')
            max_results: Maximum number of results
            start_date: Filter papers after this date (YYYY-MM-DD format)

        Returns:
            List of paper metadata dictionaries
        """
        query = f"cat:{category}"

        if start_date:
            query += f" AND submittedDate:[{start_date} TO *]"

        return self.search_papers(
            query=query,
            max_results=max_results,
            sort_by="submittedDate",
            sort_order="descending",
        )

    def search_by_author(
        self, author_name: str, max_results: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search for papers by author

        Args:
            author_name: Author name
            max_results: Maximum number of results

        Returns:
            List of paper metadata dictionaries
        """
        query = f"au:{author_name}"

        return self.search_papers(
            query=query,
            max_results=max_results,
            sort_by="submittedDate",
            sort_order="descending",
        )

    def get_trending_papers(
        self, categories: List[str], days_back: int = 7, max_results: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get trending papers from specific categories in the last N days

        Args:
            categories: List of arXiv categories
            days_back: Number of days to look back
            max_results: Maximum number of results

        Returns:
            List of paper metadata dictionaries
        """
        # Calculate start date
        start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y%m%d")

        # Build category query
        category_query = " OR ".join([f"cat:{cat}" for cat in categories])
        query = f"({category_query}) AND submittedDate:[{start_date} TO *]"

        return self.search_papers(
            query=query,
            max_results=max_results,
            sort_by="submittedDate",
            sort_order="descending",
        )

    def _parse_paper_result(self, result: Any) -> Dict[str, Any]:
        """Parse arXiv API result into our paper format"""

        # Extract arXiv ID
        arxiv_id = result.get_short_id()

        # Extract categories
        categories = [cat for cat in result.categories]
        primary_category = result.primary_category

        # Extract authors
        authors = [author.name for author in result.authors]

        # Extract dates
        published = result.published
        updated = result.updated

        # Extract URLs
        pdf_url = result.pdf_url
        entry_url = result.entry_id

        # Build paper dictionary
        paper = {
            "arxiv_id": arxiv_id,
            "title": result.title,
            "abstract": result.summary,
            "authors": authors,
            "categories": categories,
            "primary_category": primary_category,
            "published_date": published.isoformat() if published else None,
            "updated_date": updated.isoformat() if updated else None,
            "pdf_url": pdf_url,
            "entry_url": entry_url,
            "comment": result.comment,
            "journal_ref": result.journal_ref,
            "doi": result.doi,
        }

        return paper

    @staticmethod
    def extract_arxiv_id_from_url(url: str) -> Optional[str]:
        """Extract arXiv ID from a URL"""
        # Patterns for arXiv URLs
        patterns = [
            r"arxiv\.org/abs/(\d{4}\.\d{4,5})",
            r"arxiv\.org/pdf/(\d{4}\.\d{4,5})",
            r"arxiv\.org/abs/([a-z\-]+/\d{7})",
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        return None

    @staticmethod
    def get_available_categories() -> Dict[str, List[str]]:
        """Get list of available arXiv categories organized by domain"""
        return {
            "Computer Science": [
                "cs.AI",  # Artificial Intelligence
                "cs.CL",  # Computation and Language
                "cs.CV",  # Computer Vision
                "cs.LG",  # Machine Learning
                "cs.NE",  # Neural and Evolutionary Computing
                "cs.IR",  # Information Retrieval
                "cs.RO",  # Robotics
                "cs.DB",  # Databases
                "cs.CR",  # Cryptography and Security
                "cs.HC",  # Human-Computer Interaction
            ],
            "Mathematics": [
                "math.ST",  # Statistics Theory
                "math.OC",  # Optimization and Control
                "math.PR",  # Probability
            ],
            "Statistics": [
                "stat.ML",  # Machine Learning
                "stat.AP",  # Applications
                "stat.CO",  # Computation
            ],
            "Physics": [
                "physics.comp-ph",  # Computational Physics
                "physics.data-an",  # Data Analysis
            ],
            "Quantitative Biology": [
                "q-bio.QM",  # Quantitative Methods
                "q-bio.NC",  # Neurons and Cognition
            ],
            "Economics": [
                "econ.EM",  # Econometrics
            ],
        }


# Global ArXiv client instance
arxiv_client = ArXivClient()


def search_arxiv(
    query: str, max_results: int = 10, categories: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """Search arXiv for papers"""
    return arxiv_client.search_papers(query, max_results, categories=categories)


def get_arxiv_paper(arxiv_id: str) -> Optional[Dict[str, Any]]:
    """Get a single paper by ID"""
    return arxiv_client.get_paper_by_id(arxiv_id)


def download_arxiv_pdf(arxiv_id: str) -> Optional[str]:
    """Download PDF for a paper"""
    return arxiv_client.download_paper(arxiv_id)


def get_trending_ai_papers(
    days_back: int = 7, max_results: int = 50
) -> List[Dict[str, Any]]:
    """Get trending AI/ML papers"""
    categories = ["cs.AI", "cs.LG", "cs.CL", "cs.CV", "stat.ML"]
    return arxiv_client.get_trending_papers(categories, days_back, max_results)
