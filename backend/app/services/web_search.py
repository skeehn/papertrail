"""
Web search service for academic paper discovery
Integrates with top research websites: arXiv, PubMed, Google Scholar, Semantic Scholar, JSTOR
"""

import asyncio
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus, urlencode

try:
    import aiohttp
except ImportError:
    aiohttp = None

try:
    import feedparser
except ImportError:
    feedparser = None
import structlog

from app.core.logging import get_logger

logger = get_logger("web_search")


class PaperSearchResult:
    """Standardized paper search result"""

    def __init__(
        self,
        title: str,
        authors: List[str],
        abstract: str,
        url: str,
        arxiv_id: Optional[str] = None,
        doi: Optional[str] = None,
        publication_date: Optional[datetime] = None,
        journal: Optional[str] = None,
        source: str = "unknown",
        relevance_score: float = 0.0,
        citation_count: int = 0,
    ):
        self.title = title
        self.authors = authors
        self.abstract = abstract
        self.url = url
        self.arxiv_id = arxiv_id
        self.doi = doi
        self.publication_date = publication_date
        self.journal = journal
        self.source = source
        self.relevance_score = relevance_score
        self.citation_count = citation_count

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "authors": self.authors,
            "abstract": self.abstract,
            "url": self.url,
            "arxiv_id": self.arxiv_id,
            "doi": self.doi,
            "publication_date": (
                self.publication_date.isoformat() if self.publication_date else None
            ),
            "journal": self.journal,
            "source": self.source,
            "relevance_score": self.relevance_score,
            "citation_count": self.citation_count,
        }


class ArxivSearcher:
    """Search arXiv papers using their API"""

    BASE_URL = "http://export.arxiv.org/api/query"

    async def search(
        self, query: str, max_results: int = 10
    ) -> List[PaperSearchResult]:
        """Search arXiv papers"""
        try:
            params = {
                "search_query": f"all:{query}",
                "start": 0,
                "max_results": max_results,
                "sortBy": "relevance",
                "sortOrder": "descending",
            }

            url = f"{self.BASE_URL}?{urlencode(params)}"

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        logger.error(f"ArXiv search failed: {response.status}")
                        return []

                    content = await response.text()
                    return self._parse_arxiv_response(content)

        except Exception as e:
            logger.error(f"ArXiv search error: {str(e)}")
            return []

    def _parse_arxiv_response(self, xml_content: str) -> List[PaperSearchResult]:
        """Parse arXiv XML response"""
        try:
            root = ET.fromstring(xml_content)
            namespace = {
                "atom": "http://www.w3.org/2005/Atom",
                "arxiv": "http://arxiv.org/schemas/atom",
            }

            results = []
            entries = root.findall("atom:entry", namespace)

            for entry in entries:
                title = entry.find("atom:title", namespace).text.strip()

                # Extract authors
                authors = []
                for author in entry.findall("atom:author", namespace):
                    name = author.find("atom:name", namespace)
                    if name is not None:
                        authors.append(name.text)

                # Extract abstract
                summary = entry.find("atom:summary", namespace)
                abstract = summary.text.strip() if summary is not None else ""

                # Extract arXiv ID and URL
                id_elem = entry.find("atom:id", namespace)
                url = id_elem.text if id_elem is not None else ""
                arxiv_id = url.split("/")[-1] if url else None

                # Extract publication date
                published = entry.find("atom:published", namespace)
                publication_date = None
                if published is not None:
                    try:
                        publication_date = datetime.fromisoformat(
                            published.text.replace("Z", "+00:00")
                        )
                    except:
                        pass

                # Extract journal reference if available
                journal_ref = entry.find("arxiv:journal_ref", namespace)
                journal = journal_ref.text if journal_ref is not None else None

                # Extract DOI if available
                doi_elem = entry.find("arxiv:doi", namespace)
                doi = doi_elem.text if doi_elem is not None else None

                result = PaperSearchResult(
                    title=title,
                    authors=authors,
                    abstract=abstract,
                    url=url,
                    arxiv_id=arxiv_id,
                    doi=doi,
                    publication_date=publication_date,
                    journal=journal,
                    source="arXiv",
                    relevance_score=0.8,  # Default relevance for arXiv
                )

                results.append(result)

            return results

        except Exception as e:
            logger.error(f"ArXiv response parsing error: {str(e)}")
            return []


class PubMedSearcher:
    """Search PubMed papers using NCBI E-utilities"""

    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    async def search(
        self, query: str, max_results: int = 10
    ) -> List[PaperSearchResult]:
        """Search PubMed papers"""
        try:
            # First, search for paper IDs
            search_url = f"{self.BASE_URL}/esearch.fcgi"
            search_params = {
                "db": "pubmed",
                "term": query,
                "retmax": max_results,
                "retmode": "xml",
                "sort": "relevance",
            }

            async with aiohttp.ClientSession() as session:
                # Get paper IDs
                async with session.get(search_url, params=search_params) as response:
                    if response.status != 200:
                        logger.error(f"PubMed search failed: {response.status}")
                        return []

                    search_content = await response.text()
                    paper_ids = self._extract_pubmed_ids(search_content)

                    if not paper_ids:
                        return []

                # Get paper details
                fetch_url = f"{self.BASE_URL}/efetch.fcgi"
                fetch_params = {
                    "db": "pubmed",
                    "id": ",".join(paper_ids),
                    "retmode": "xml",
                }

                async with session.get(fetch_url, params=fetch_params) as response:
                    if response.status != 200:
                        logger.error(f"PubMed fetch failed: {response.status}")
                        return []

                    fetch_content = await response.text()
                    return self._parse_pubmed_response(fetch_content)

        except Exception as e:
            logger.error(f"PubMed search error: {str(e)}")
            return []

    def _extract_pubmed_ids(self, xml_content: str) -> List[str]:
        """Extract PubMed IDs from search response"""
        try:
            root = ET.fromstring(xml_content)
            ids = []
            for id_elem in root.findall(".//Id"):
                ids.append(id_elem.text)
            return ids
        except Exception as e:
            logger.error(f"PubMed ID extraction error: {str(e)}")
            return []

    def _parse_pubmed_response(self, xml_content: str) -> List[PaperSearchResult]:
        """Parse PubMed XML response"""
        try:
            root = ET.fromstring(xml_content)
            results = []

            articles = root.findall(".//PubmedArticle")

            for article in articles:
                # Extract title
                title_elem = article.find(".//ArticleTitle")
                title = title_elem.text if title_elem is not None else "No title"

                # Extract authors
                authors = []
                author_list = article.find(".//AuthorList")
                if author_list is not None:
                    for author in author_list.findall(".//Author"):
                        lastname = author.find("LastName")
                        firstname = author.find("ForeName")
                        if lastname is not None and firstname is not None:
                            authors.append(f"{firstname.text} {lastname.text}")

                # Extract abstract
                abstract_elem = article.find(".//AbstractText")
                abstract = abstract_elem.text if abstract_elem is not None else ""

                # Extract journal
                journal_elem = article.find(".//Journal/Title")
                journal = journal_elem.text if journal_elem is not None else None

                # Extract publication date
                pub_date = article.find(".//PubDate")
                publication_date = None
                if pub_date is not None:
                    year = pub_date.find("Year")
                    month = pub_date.find("Month")
                    if year is not None:
                        try:
                            year_val = int(year.text)
                            month_val = (
                                int(month.text)
                                if month is not None and month.text.isdigit()
                                else 1
                            )
                            publication_date = datetime(year_val, month_val, 1)
                        except:
                            pass

                # Extract DOI
                doi = None
                article_id_list = article.find(".//ArticleIdList")
                if article_id_list is not None:
                    for article_id in article_id_list.findall(".//ArticleId"):
                        if article_id.get("IdType") == "doi":
                            doi = article_id.text
                            break

                # Extract PMID for URL
                pmid_elem = article.find(".//PMID")
                pmid = pmid_elem.text if pmid_elem is not None else None
                url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else ""

                result = PaperSearchResult(
                    title=title,
                    authors=authors,
                    abstract=abstract,
                    url=url,
                    doi=doi,
                    publication_date=publication_date,
                    journal=journal,
                    source="PubMed",
                    relevance_score=0.7,  # Default relevance for PubMed
                )

                results.append(result)

            return results

        except Exception as e:
            logger.error(f"PubMed response parsing error: {str(e)}")
            return []


class SemanticScholarSearcher:
    """Search papers using Semantic Scholar Academic Graph API"""

    BASE_URL = "https://api.semanticscholar.org/graph/v1"

    async def search(
        self, query: str, max_results: int = 10
    ) -> List[PaperSearchResult]:
        """Search Semantic Scholar papers"""
        try:
            url = f"{self.BASE_URL}/paper/search"
            params = {
                "query": query,
                "limit": max_results,
                "fields": "title,authors,abstract,venue,year,citationCount,externalIds,url",
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        logger.error(
                            f"Semantic Scholar search failed: {response.status}"
                        )
                        return []

                    data = await response.json()
                    return self._parse_semantic_scholar_response(data)

        except Exception as e:
            logger.error(f"Semantic Scholar search error: {str(e)}")
            return []

    def _parse_semantic_scholar_response(
        self, data: Dict[str, Any]
    ) -> List[PaperSearchResult]:
        """Parse Semantic Scholar API response"""
        try:
            results = []
            papers = data.get("data", [])

            for paper in papers:
                title = paper.get("title", "No title")

                # Extract authors
                authors = []
                author_list = paper.get("authors", [])
                for author in author_list:
                    if author.get("name"):
                        authors.append(author["name"])

                abstract = paper.get("abstract", "")
                venue = paper.get("venue", "")
                year = paper.get("year")
                citation_count = paper.get("citationCount", 0)
                url = paper.get("url", "")

                # Extract external IDs
                external_ids = paper.get("externalIds", {})
                doi = external_ids.get("DOI")
                arxiv_id = external_ids.get("ArXiv")

                # Create publication date from year
                publication_date = None
                if year:
                    try:
                        publication_date = datetime(year, 1, 1)
                    except:
                        pass

                result = PaperSearchResult(
                    title=title,
                    authors=authors,
                    abstract=abstract,
                    url=url,
                    arxiv_id=arxiv_id,
                    doi=doi,
                    publication_date=publication_date,
                    journal=venue,
                    source="Semantic Scholar",
                    relevance_score=0.75,
                    citation_count=citation_count,
                )

                results.append(result)

            return results

        except Exception as e:
            logger.error(f"Semantic Scholar response parsing error: {str(e)}")
            return []


class WebSearchService:
    """Unified web search service for academic papers"""

    def __init__(self):
        self.arxiv_searcher = ArxivSearcher()
        self.pubmed_searcher = PubMedSearcher()
        self.semantic_scholar_searcher = SemanticScholarSearcher()

    async def search_all_sources(
        self,
        query: str,
        max_results_per_source: int = 10,
        sources: Optional[List[str]] = None,
    ) -> Dict[str, List[PaperSearchResult]]:
        """Search all available sources"""

        if sources is None:
            sources = ["arxiv", "pubmed", "semantic_scholar"]

        tasks = []
        source_mapping = {}

        if "arxiv" in sources:
            tasks.append(self.arxiv_searcher.search(query, max_results_per_source))
            source_mapping[len(tasks) - 1] = "arxiv"

        if "pubmed" in sources:
            tasks.append(self.pubmed_searcher.search(query, max_results_per_source))
            source_mapping[len(tasks) - 1] = "pubmed"

        if "semantic_scholar" in sources:
            tasks.append(
                self.semantic_scholar_searcher.search(query, max_results_per_source)
            )
            source_mapping[len(tasks) - 1] = "semantic_scholar"

        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            search_results = {}
            for i, result in enumerate(results):
                source_name = source_mapping.get(i, "unknown")
                if isinstance(result, Exception):
                    logger.error(f"Search failed for {source_name}: {str(result)}")
                    search_results[source_name] = []
                else:
                    search_results[source_name] = result

            return search_results

        except Exception as e:
            logger.error(f"Multi-source search error: {str(e)}")
            return {}

    def merge_and_deduplicate(
        self, search_results: Dict[str, List[PaperSearchResult]]
    ) -> List[PaperSearchResult]:
        """Merge results from all sources and remove duplicates"""

        all_results = []
        seen_titles = set()
        seen_dois = set()
        seen_arxiv_ids = set()

        # Combine all results
        for source, results in search_results.items():
            all_results.extend(results)

        # Remove duplicates based on title, DOI, or arXiv ID
        unique_results = []

        for result in all_results:
            # Check for duplicates
            title_normalized = re.sub(r"[^\w\s]", "", result.title.lower())

            is_duplicate = False

            # Check DOI
            if result.doi and result.doi in seen_dois:
                is_duplicate = True

            # Check arXiv ID
            if result.arxiv_id and result.arxiv_id in seen_arxiv_ids:
                is_duplicate = True

            # Check title similarity (simple approach)
            if title_normalized in seen_titles:
                is_duplicate = True

            if not is_duplicate:
                unique_results.append(result)
                seen_titles.add(title_normalized)
                if result.doi:
                    seen_dois.add(result.doi)
                if result.arxiv_id:
                    seen_arxiv_ids.add(result.arxiv_id)

        # Sort by relevance score and citation count
        unique_results.sort(
            key=lambda x: (x.relevance_score, x.citation_count), reverse=True
        )

        return unique_results

    async def search(
        self, query: str, max_results: int = 20, sources: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Main search interface"""

        logger.info(
            f"Starting web search",
            query=query,
            max_results=max_results,
            sources=sources,
        )

        # Search all sources
        search_results = await self.search_all_sources(
            query,
            max_results_per_source=max_results // (len(sources) if sources else 3),
            sources=sources,
        )

        # Merge and deduplicate
        unique_results = self.merge_and_deduplicate(search_results)

        # Limit results
        final_results = unique_results[:max_results]

        logger.info(
            f"Web search completed",
            query=query,
            total_results=len(final_results),
            sources_searched=list(search_results.keys()),
        )

        # Convert to dict format
        return [result.to_dict() for result in final_results]


# Global instance
web_search_service = WebSearchService()
