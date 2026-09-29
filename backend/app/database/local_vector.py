"""Local instant vector store: FastEmbed (ONNX) + LanceDB.

HydraDB's cloud ingest is async (202 queued, minutes to hours before a
source becomes searchable). This store embeds papers locally the moment
they are ingested, so library search works instantly and survives the
cloud queue entirely.

Data lives under ~/.papertrail/vector_db (override via PAPERTRAIL_VECTOR_DIR).
All methods degrade to a no-op when the optional deps are missing, keeping
the ingest path safe even on a bare checkout.
"""

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

from app.core.logging import get_logger

logger = get_logger("local_vector")


def _stable_id(arxiv_id: str) -> str:
    """Normalize 1706.03762v7 -> 1706.03762 so re-indexed versions dedupe."""
    return re.sub(r"v\d+$", "", arxiv_id or "")

try:
    import lancedb

    _LANCEDB_OK = True
except ImportError:  # pragma: no cover
    _LANCEDB_OK = False

try:
    from fastembed import TextEmbedding

    _FASTEMBED_OK = True
except ImportError:  # pragma: no cover
    _FASTEMBED_OK = False

_EMBED_MODEL = "BAAI/bge-small-en-v1.5"
_EMBED_DIM = 384


class LocalVectorStore:
    """Embedded paper library with instant semantic search."""

    TABLE = "papers"

    def __init__(self) -> None:
        self._db: Any = None
        self._table: Any = None
        self._model: Any = None
        self._failed = False
        self.dir = Path(
            os.environ.get("PAPERTRAIL_VECTOR_DIR")
            or Path.home() / ".papertrail" / "vector_db"
        )

    @property
    def _available(self) -> bool:
        return _LANCEDB_OK and _FASTEMBED_OK

    def _get_embedder(self) -> Any:
        if self._model is None:
            self._model = TextEmbedding(model_name=_EMBED_MODEL)
        return self._model

    def _get_table(self) -> Any:
        if self._table is not None:
            return self._table
        self.dir.mkdir(parents=True, exist_ok=True)
        self._db = lancedb.connect(str(self.dir))
        if self.TABLE in self._db.table_names():
            self._table = self._db.open_table(self.TABLE)
        else:
            self._table = self._db.create_table(self.TABLE, schema=self._schema())
        return self._table

    @staticmethod
    def _schema() -> Any:
        import pyarrow as pa

        return pa.schema(
            [
                ("arxiv_id", pa.string()),
                ("title", pa.string()),
                ("authors", pa.string()),
                ("abstract", pa.string()),
                ("year", pa.string()),
                ("categories", pa.string()),
                ("vector", pa.list_(pa.float32(), _EMBED_DIM)),
            ]
        )

    def _embed(self, texts: List[str]) -> List[List[float]]:
        return [list(vec) for vec in self._get_embedder().embed(texts)]

    async def upsert_paper(self, paper: Dict[str, Any]) -> bool:
        """Embed + upsert one paper. Returns True when written locally."""
        if not self._available:
            logger.debug("Local vector deps missing - skipping local upsert")
            return False
        try:
            arxiv_id = _stable_id(paper.get("arxiv_id"))
            text = f"{paper.get('title', '')}. {paper.get('abstract', '')}"
            if not arxiv_id or not text.strip(". "):
                return False

            authors = paper.get("authors", [])
            if isinstance(authors, list):
                authors = ", ".join(authors)
            row = {
                "arxiv_id": arxiv_id,
                "title": paper.get("title", ""),
                "authors": authors,
                "abstract": paper.get("abstract", ""),
                "year": str(paper.get("year") or ""),
                "categories": ", ".join(paper.get("categories", []) or []),
                "vector": self._embed([text])[0],
            }
            table = self._get_table()
            table.delete(f"arxiv_id = '{arxiv_id}'")
            table.add([row])
            logger.debug("Paper embedded locally", arxiv_id=arxiv_id)
            return True
        except Exception as e:  # noqa: BLE001
            logger.warning("Local vector upsert failed", error=str(e))
            return False

    async def search(self, query: str, limit: int = 6) -> List[Dict[str, Any]]:
        """Semantic search; tiny results mean nothing written locally yet."""
        if not self._available:
            return []
        try:
            table = self._get_table()
            sv = self._embed([query])
            hits = table.search(sv[0]).limit(limit).to_list()
            results = []
            for hit in hits:
                results.append(
                    {
                        "arxiv_id": hit.get("arxiv_id", ""),
                        "title": hit.get("title", ""),
                        "abstract": (hit.get("abstract") or "")[:1200],
                        "authors": hit.get("authors", ""),
                        "score": round(max(0.0, 1.0 - float(hit.get("_distance", 1.0))), 4),
                    }
                )
            return results
        except Exception as e:  # noqa: BLE001
            logger.warning("Local vector search failed", error=str(e))
            return []

    async def list_papers(self, skip: int = 0, limit: int = 50) -> List[Dict[str, Any]]:
        """List every locally embedded paper, newest first."""
        if not self._available:
            return []
        try:
            table = self._get_table()
            rows = table.to_arrow().to_pylist()
            rows.sort(key=lambda r: r.get("title") or "", reverse=False)
            out = []
            for row in rows[skip : skip + limit]:
                authors_raw = row.get("authors", "")
                authors = (
                    authors_raw if isinstance(authors_raw, list) else [a.strip() for a in authors_raw.split(",") if a.strip()]
                )
                out.append(
                    {
                        "id": row.get("arxiv_id", ""),
                        "arxiv_id": row.get("arxiv_id", ""),
                        "title": row.get("title", ""),
                        "authors": authors,
                        "abstract": (row.get("abstract") or "")[:500],
                        "year": row.get("year", ""),
                        "score": 1.0,
                    }
                )
            return out

        except Exception as e:  # noqa: BLE001
            logger.warning("Local vector list failed", error=str(e))
            return []

    async def count(self) -> int:
        if not self._available:
            return 0
        try:
            table = self._get_table()
            return table.count_rows()
        except Exception:  # noqa: BLE001
            return 0


local_vector_store = LocalVectorStore()
