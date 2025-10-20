import os
import re
import tempfile
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import fitz  # PyMuPDF
import httpx
import structlog

from app.core.config import settings
from app.core.logging import get_logger


@dataclass
class ExtractedSection:
    """Data class for extracted paper sections"""

    title: str
    content: str
    confidence: float
    start_page: int
    end_page: int


class PDFProcessor:
    """PDF processing service for academic papers"""

    def __init__(self):
        self.logger = get_logger("pdf_processor")

        # Common section headers in academic papers
        self.section_patterns = {
            "abstract": [
                r"^abstract$",
                r"^summary$",
            ],
            "introduction": [
                r"^introduction$",
                r"^1\.?\s*introduction",
            ],
            "methodology": [
                r"^methodology$",
                r"^methods?$",
                r"^approach$",
                r"^model$",
                r"^framework$",
                r"^\d+\.?\s*method",
                r"^\d+\.?\s*approach",
            ],
            "results": [
                r"^results?$",
                r"^experiments?$",
                r"^evaluation$",
                r"^findings$",
                r"^\d+\.?\s*results?",
                r"^\d+\.?\s*experiments?",
            ],
            "discussion": [
                r"^discussion$",
                r"^analysis$",
                r"^\d+\.?\s*discussion",
            ],
            "conclusion": [
                r"^conclusions?$",
                r"^concluding\s+remarks?$",
                r"^\d+\.?\s*conclusions?",
            ],
            "references": [
                r"^references$",
                r"^bibliography$",
                r"^works?\s+cited$",
            ],
        }

    async def process_file(self, file_path: str) -> Dict[str, Any]:
        """Process a local PDF file"""
        try:
            self.logger.info("Processing PDF file", file_path=file_path)

            if not os.path.exists(file_path):
                raise FileNotFoundError(f"PDF file not found: {file_path}")

            # Extract text and metadata from PDF
            doc = fitz.open(file_path)

            # Extract metadata
            metadata = self._extract_metadata(doc)

            # Extract full text
            full_text = self._extract_full_text(doc)

            # Extract sections
            sections = self._extract_sections(doc)

            # Extract citations
            citations = self._extract_citations(full_text)

            doc.close()

            # Generate paper ID (use filename if no arXiv ID)
            paper_id = (
                metadata.get("arxiv_id")
                or os.path.splitext(os.path.basename(file_path))[0]
            )

            result = {
                "arxiv_id": paper_id,
                "title": metadata.get("title", ""),
                "authors": metadata.get("authors", []),
                "abstract": sections.get("abstract", ""),
                "text": full_text,
                "sections": sections,
                "citations": citations,
                "publication_date": metadata.get("publication_date"),
                "journal": metadata.get("journal"),
                "doi": metadata.get("doi"),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "file_path": file_path,
                "processing_stats": {
                    "page_count": len(doc),
                    "text_length": len(full_text),
                    "sections_found": len(sections),
                    "citations_found": len(citations),
                },
            }

            self.logger.info(
                "PDF processing completed",
                paper_id=paper_id,
                page_count=len(doc),
                text_length=len(full_text),
            )

            return result

        except Exception as e:
            self.logger.error(
                "PDF processing failed", error=str(e), file_path=file_path
            )
            raise

    async def download_from_arxiv(self, arxiv_id: str) -> Dict[str, Any]:
        """Download and process paper from arXiv"""
        try:
            self.logger.info("Downloading from arXiv", arxiv_id=arxiv_id)

            # Clean arXiv ID (remove version if present)
            clean_arxiv_id = arxiv_id.split("v")[0]

            # Download PDF from arXiv
            pdf_url = f"https://arxiv.org/pdf/{clean_arxiv_id}.pdf"

            async with httpx.AsyncClient(timeout=30.0) as client:
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=".pdf"
                ) as tmp_file:
                    async with client.stream("GET", pdf_url) as response:
                        response.raise_for_status()

                        async for chunk in response.aiter_bytes(chunk_size=8192):
                            tmp_file.write(chunk)

                    tmp_file_path = tmp_file.name

            try:
                # Process the downloaded PDF
                result = await self.process_file(tmp_file_path)

                # Fetch additional metadata from arXiv API
                arxiv_metadata = await self._fetch_arxiv_metadata(clean_arxiv_id)

                # Merge arXiv metadata
                result.update(
                    {
                        "arxiv_id": clean_arxiv_id,
                        "title": arxiv_metadata.get("title", result["title"]),
                        "authors": arxiv_metadata.get("authors", result["authors"]),
                        "abstract": arxiv_metadata.get("abstract", result["abstract"]),
                        "publication_date": arxiv_metadata.get(
                            "publication_date", result["publication_date"]
                        ),
                        "journal": arxiv_metadata.get("journal", result["journal"]),
                        "doi": arxiv_metadata.get("doi", result["doi"]),
                        "categories": arxiv_metadata.get("categories", []),
                    }
                )

                return result

            finally:
                # Clean up temporary file
                if os.path.exists(tmp_file_path):
                    os.unlink(tmp_file_path)

        except Exception as e:
            self.logger.error("arXiv download failed", error=str(e), arxiv_id=arxiv_id)
            raise

    def _extract_metadata(self, doc: fitz.Document) -> Dict[str, Any]:
        """Extract metadata from PDF"""
        metadata = {}

        try:
            # Extract PDF metadata
            pdf_meta = doc.metadata

            if pdf_meta.get("title"):
                metadata["title"] = pdf_meta["title"].strip()

            if pdf_meta.get("author"):
                # Split authors by common separators
                authors_str = pdf_meta["author"]
                authors = [
                    a.strip() for a in re.split(r"[,;&]", authors_str) if a.strip()
                ]
                metadata["authors"] = authors

            if pdf_meta.get("creationDate"):
                try:
                    # Parse PDF creation date
                    date_str = pdf_meta["creationDate"].replace("D:", "")
                    if len(date_str) >= 8:
                        year = int(date_str[:4])
                        month = int(date_str[4:6])
                        day = int(date_str[6:8])
                        metadata["publication_date"] = datetime(year, month, day)
                except ValueError:
                    pass

            # Try to extract arXiv ID from text
            if doc.page_count > 0:
                first_page_text = doc[0].get_text()
                arxiv_match = re.search(r"arXiv:(\d{4}\.\d{4,5})", first_page_text)
                if arxiv_match:
                    metadata["arxiv_id"] = arxiv_match.group(1)

        except Exception as e:
            self.logger.warning("Failed to extract some metadata", error=str(e))

        return metadata

    def _extract_full_text(self, doc: fitz.Document) -> str:
        """Extract full text from PDF"""
        full_text = ""

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()

            # Clean up text
            text = self._clean_text(text)
            full_text += text + "\n\n"

        return full_text.strip()

    def _extract_sections(self, doc: fitz.Document) -> Dict[str, str]:
        """Extract sections from PDF using pattern matching"""
        sections = {}
        full_text = self._extract_full_text(doc)

        # Split text into lines for section detection
        lines = full_text.split("\n")
        current_section = None
        section_content = []

        for line in lines:
            line_lower = line.strip().lower()

            # Check if line matches any section pattern
            matched_section = None
            for section_name, patterns in self.section_patterns.items():
                for pattern in patterns:
                    if re.match(pattern, line_lower):
                        matched_section = section_name
                        break
                if matched_section:
                    break

            if matched_section:
                # Save previous section
                if current_section and section_content:
                    sections[current_section] = "\n".join(section_content).strip()

                # Start new section
                current_section = matched_section
                section_content = []
            elif current_section:
                # Add content to current section
                if line.strip():
                    section_content.append(line)

        # Save final section
        if current_section and section_content:
            sections[current_section] = "\n".join(section_content).strip()

        return sections

    def _extract_citations(self, text: str) -> List[Dict[str, Any]]:
        """Extract citations from text"""
        citations = []

        # Find numbered references like [1], [2], etc.
        numbered_refs = re.findall(r"\[(\d+)\]", text)

        # Find author-year citations like (Smith et al., 2020)
        author_year_refs = re.findall(
            r"\(([A-Z][a-z]+(?:\s+et\s+al\.?)?),?\s+(\d{4})\)", text
        )

        # Process numbered references
        for ref_num in set(numbered_refs):
            citations.append(
                {
                    "type": "numbered",
                    "reference": f"[{ref_num}]",
                    "number": int(ref_num),
                }
            )

        # Process author-year references
        for author, year in set(author_year_refs):
            citations.append(
                {
                    "type": "author_year",
                    "author": author,
                    "year": int(year),
                    "reference": f"({author}, {year})",
                }
            )

        return citations

    def _clean_text(self, text: str) -> str:
        """Clean and normalize extracted text"""
        # Remove excessive whitespace
        text = re.sub(r"\s+", " ", text)

        # Remove page breaks and headers/footers patterns
        text = re.sub(r"\n\d+\n", "\n", text)  # Page numbers
        text = re.sub(r"\n[A-Za-z\s]+\n\d+\n", "\n", text)  # Headers with page numbers

        # Fix common PDF extraction issues
        text = text.replace("ﬁ", "fi")
        text = text.replace("ﬂ", "fl")
        text = text.replace("–", "-")
        text = text.replace('"', '"')
        text = text.replace('"', '"')

        return text.strip()

    async def _fetch_arxiv_metadata(self, arxiv_id: str) -> Dict[str, Any]:
        """Fetch metadata from arXiv API"""
        try:
            api_url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(api_url)
                response.raise_for_status()

                # Parse XML response
                import xml.etree.ElementTree as ET

                root = ET.fromstring(response.content)

            # Extract metadata from XML
            metadata = {}

            # Find the entry element
            entry = root.find(".//{http://www.w3.org/2005/Atom}entry")
            if entry is not None:
                # Title
                title_elem = entry.find(".//{http://www.w3.org/2005/Atom}title")
                if title_elem is not None:
                    metadata["title"] = title_elem.text.strip()

                # Authors
                authors = []
                for author in entry.findall(".//{http://www.w3.org/2005/Atom}author"):
                    name_elem = author.find(".//{http://www.w3.org/2005/Atom}name")
                    if name_elem is not None:
                        authors.append(name_elem.text.strip())
                metadata["authors"] = authors

                # Abstract
                summary_elem = entry.find(".//{http://www.w3.org/2005/Atom}summary")
                if summary_elem is not None:
                    metadata["abstract"] = summary_elem.text.strip()

                # Publication date
                published_elem = entry.find(".//{http://www.w3.org/2005/Atom}published")
                if published_elem is not None:
                    try:
                        pub_date = datetime.fromisoformat(
                            published_elem.text.replace("Z", "+00:00")
                        )
                        metadata["publication_date"] = pub_date
                    except ValueError:
                        pass

                # Categories
                categories = []
                for category in entry.findall(
                    ".//{http://arxiv.org/schemas/atom}primary_category"
                ):
                    term = category.get("term")
                    if term:
                        categories.append(term)
                metadata["categories"] = categories

                # DOI (if available)
                doi_elem = entry.find(".//{http://arxiv.org/schemas/atom}doi")
                if doi_elem is not None:
                    metadata["doi"] = doi_elem.text.strip()

            return metadata

        except Exception as e:
            self.logger.warning(
                "Failed to fetch arXiv metadata", error=str(e), arxiv_id=arxiv_id
            )
            return {}

    def get_processing_stats(self, file_path: str) -> Dict[str, Any]:
        """Get basic statistics about a PDF file"""
        try:
            if not os.path.exists(file_path):
                return {"error": "File not found"}

            doc = fitz.open(file_path)
            stats = {
                "page_count": len(doc),
                "file_size": os.path.getsize(file_path),
                "has_text": any(
                    doc[i].get_text().strip() for i in range(min(3, len(doc)))
                ),  # Check first 3 pages
                "is_searchable": doc.is_pdf and not doc.needs_pass,
            }
            doc.close()

            return stats

        except Exception as e:
            return {"error": str(e)}
