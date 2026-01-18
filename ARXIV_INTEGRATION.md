# ArXiv Integration & GraphRAG Enhancement

This document describes the new ArXiv integration and GraphRAG enhancements added to Papertrail.

## New Features

### 1. ArXiv Integration

Papertrail can now automatically fetch, download, and index research papers from arXiv.

**Key Capabilities:**
- Search arXiv by query, category, or author
- Download PDFs automatically
- Fetch paper metadata (title, authors, abstract, categories, dates)
- Track trending papers by category
- Bulk indexing with background job processing

**API Endpoints:**
- `POST /api/v1/arxiv/search` - Search for papers
- `GET /api/v1/arxiv/paper/{arxiv_id}` - Get paper by ID
- `POST /api/v1/arxiv/bulk-index` - Index multiple papers
- `POST /api/v1/arxiv/index-by-search` - Search and index results
- `POST /api/v1/arxiv/index-trending` - Index trending papers
- `POST /api/v1/arxiv/index-demo-papers` - Index diverse AI papers for demo
- `GET /api/v1/arxiv/jobs/{job_id}` - Get indexing job status
- `GET /api/v1/arxiv/categories` - Get available categories

### 2. Pinecone Vector Store

Replaced FAISS with Pinecone for scalable vector search.

**Benefits:**
- Cloud-hosted, no local storage needed
- Serverless architecture
- Better scalability
- Metadata filtering
- Built-in persistence

**Configuration:**
```bash
PINECONE_API_KEY=your_api_key
PINECONE_INDEX_NAME=quickstart
PINECONE_DIMENSION=384
```

### 3. Firecrawl Web Search

Added Firecrawl for web scraping and search capabilities.

**Use Cases:**
- Scrape research paper URLs
- Search for papers beyond arXiv
- Extract paper metadata from any URL
- Crawl academic websites

**Configuration:**
```bash
FIRECRAWL_API_KEY=your_api_key
FIRECRAWL_ENABLED=True
```

### 4. Batch Processing System

Efficient bulk indexing with:
- Controlled concurrency
- Progress tracking
- Error handling
- Background job processing
- Status monitoring

### 5. Pre-Indexing Scripts

Easy setup scripts to populate the database with demo data.

**Usage:**
```bash
# Quick demo (20 papers)
python scripts/preindex_demo_papers.py --quick

# Standard demo (100 papers)
python scripts/preindex_demo_papers.py

# Custom topics
python scripts/preindex_demo_papers.py --topics "transformers" "graph neural networks" --max-papers 50

# Test services
python scripts/test_services.py
```

## Setup Instructions

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Environment

Update `.env` file with API keys:

```bash
# Pinecone
PINECONE_API_KEY=pcsk_...
PINECONE_INDEX_NAME=quickstart
PINECONE_DIMENSION=384

# Firecrawl (optional)
FIRECRAWL_API_KEY=fc-...
FIRECRAWL_ENABLED=True

# ArXiv (no key needed)
ARXIV_MAX_RESULTS=100
ARXIV_RATE_LIMIT=3.0
ARXIV_DOWNLOAD_DIR=./data/arxiv_pdfs
```

### 3. Initialize Services

```bash
# Test services
python scripts/test_services.py

# If tests pass, index demo papers
python scripts/preindex_demo_papers.py --quick
```

### 4. Start the Server

```bash
# Backend
uvicorn app.main:app --reload --port 8000

# Frontend (in separate terminal)
cd ../frontend
npm run dev
```

## Usage Examples

### Search arXiv via API

```python
import requests

# Search for papers
response = requests.post(
    "http://localhost:8000/api/v1/arxiv/search",
    json={
        "query": "graph neural networks",
        "max_results": 10,
        "categories": ["cs.LG", "cs.AI"]
    }
)

papers = response.json()
for paper in papers:
    print(f"{paper['title']} ({paper['arxiv_id']})")
```

### Index Papers

```python
# Index specific papers
response = requests.post(
    "http://localhost:8000/api/v1/arxiv/bulk-index",
    json={
        "arxiv_ids": ["1706.03762", "1810.04805", "2005.14165"]
    }
)

job_id = response.json()["job_id"]

# Check status
status = requests.get(f"http://localhost:8000/api/v1/arxiv/jobs/{job_id}").json()
print(f"Progress: {status['processed']}/{status['total_papers']}")
```

### Search and Index

```python
# Search and automatically index results
response = requests.post(
    "http://localhost:8000/api/v1/arxiv/index-by-search",
    json={
        "query": "retrieval augmented generation",
        "max_results": 50,
        "categories": ["cs.CL", "cs.AI"]
    }
)
```

## Architecture

```
User Request
    ↓
FastAPI Endpoint (/api/v1/arxiv/*)
    ↓
ArXiv Client → Download PDFs
    ↓
PDF Processor → Extract text & sections
    ↓
Entity Extractor → Extract entities & relationships
    ↓
┌─────────────────────┬─────────────────────┐
│   Graph Builder     │   Vector Indexer    │
│   (Neo4j)           │   (Pinecone)        │
└─────────────────────┴─────────────────────┘
```

## File Structure

```
backend/
├── app/
│   ├── services/
│   │   ├── arxiv_client.py           # ArXiv API client
│   │   ├── arxiv_indexer.py          # Batch processing
│   │   └── firecrawl_service.py      # Web scraping
│   ├── database/
│   │   └── pinecone_store.py         # Pinecone integration
│   └── api/v1/endpoints/
│       └── arxiv.py                  # ArXiv endpoints
└── scripts/
    ├── preindex_demo_papers.py       # Pre-indexing script
    └── test_services.py              # Service tests
```

## Performance Considerations

### Rate Limiting

- arXiv: 3 requests/second (configurable)
- Concurrent processing: 4 workers (configurable)

### Batch Processing

- Processes papers in parallel with controlled concurrency
- Background jobs for large batches
- Progress tracking and error recovery

### Vector Store

- Batch upserts to Pinecone (100 vectors at a time)
- Metadata stored for filtering
- Automatic retries on failures

## Troubleshooting

### Common Issues

**1. Pinecone Connection Error**
```bash
# Check API key is set
echo $PINECONE_API_KEY

# Verify index exists
# Go to https://app.pinecone.io/
```

**2. ArXiv Rate Limiting**
```bash
# Reduce rate in .env
ARXIV_RATE_LIMIT=2.0  # slower but safer
```

**3. PDF Download Failures**
```bash
# Check download directory exists
mkdir -p data/arxiv_pdfs

# Check disk space
df -h
```

**4. Missing Dependencies**
```bash
pip install pinecone arxiv firecrawl-py
```

## Demo Topics

The pre-indexing script covers these AI/ML topics:

1. Large Language Models & Transformers
2. Graph Neural Networks
3. Retrieval Augmented Generation (RAG)
4. Few-Shot Learning & Meta-Learning
5. Reinforcement Learning
6. Computer Vision & Object Detection
7. Natural Language Processing
8. Multimodal Learning (Vision + Language)
9. Neural Architecture Search (AutoML)
10. Explainable AI & Interpretability
11. Contrastive Learning & Self-Supervised Learning
12. Attention Mechanisms

Plus influential papers:
- Attention is All You Need (Transformers)
- BERT
- GPT-3
- Adam Optimizer
- CLIP
- ResNet
- ViT (Vision Transformer)
- And more...

## Next Steps

### Phase 2 Enhancements (Coming Soon)

1. **Community Detection**
   - Identify research communities/topics automatically
   - Cluster related papers and entities
   - Generate community summaries

2. **Multi-Hop Reasoning**
   - Answer complex queries across multiple papers
   - Find connections between distant concepts
   - Graph traversal for deeper insights

3. **Trend Detection**
   - Track entity popularity over time
   - Identify emerging research areas
   - Performance improvements by year

4. **Contradiction & Consensus**
   - Find conflicting claims
   - Identify research consensus
   - Surface controversial topics

5. **Research Gap Analysis**
   - Identify understudied areas
   - Suggest research directions
   - Find missing connections

## Support

For issues or questions:
1. Check logs: `tail -f backend/logs/*.log`
2. Run tests: `python scripts/test_services.py`
3. Verify config: `cat .env | grep -E "(PINECONE|ARXIV|FIRECRAWL)"`

## License

Same as Papertrail project license.
