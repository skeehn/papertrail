# Papertrail Setup Guide

Complete guide to setting up and running Papertrail with ArXiv integration, Neo4j, and OpenRouter.

## Prerequisites

- Python 3.8+
- Node.js 16+
- Internet connection for API access

## Step 1: Install Backend Dependencies

```bash
cd backend
pip install -r requirements.txt
```

Required packages:
- `fastapi` - Web framework
- `neo4j` - Graph database client
- `openai` - LLM client (works with OpenRouter)
- `pinecone-client` - Vector database
- `arxiv` - ArXiv API client
- `firecrawl-py` - Web scraping
- `sentence-transformers` - Embeddings
- And more...

## Step 2: Configure Environment Variables

The `.env` file in the `backend/` directory contains all configuration:

### Required Configuration

```bash
# Neo4j Database (Cloud)
NEO4J_URI=neo4j+s://85da7327.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=pcJR-Ag3HCFkHLCY2-_YdbvePns7w1ThoB34aozaGsw
NEO4J_DATABASE=neo4j

# OpenRouter (for OpenAI-compatible models)
OPENAI_API_KEY=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
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_MODEL=openai/gpt-4-turbo-preview

# Pinecone (Vector Database)
PINECONE_API_KEY=pcsk_5re6Dq_CUZ1oWcTPtUc2rVftcD2RuDPMwLwLhY3ubpnPiFy3nMBMoWPNff3h76stgtR9rM
PINECONE_INDEX_NAME=quickstart

# Firecrawl (Web Scraping - Optional)
FIRECRAWL_API_KEY=fc-d847c9daa2714f7f9a26d440a86a7695
FIRECRAWL_ENABLED=True
```

### Optional Configuration

```bash
# Redis LangCache (Semantic Caching - Optional)
LANGCACHE_API_KEY=<your_key>
LANGCACHE_SERVER_URL=https://aws-us-east-1.langcache.redis.io
LANGCACHE_CACHE_ID=<your_cache_id>
LANGCACHE_ENABLED=True

# ArXiv Settings
ARXIV_MAX_RESULTS=100
ARXIV_RATE_LIMIT=3.0
ARXIV_DOWNLOAD_DIR=./data/arxiv_pdfs

# Processing
MAX_CONCURRENT_PROCESSES=4
BATCH_SIZE=10
```

## Step 3: Test Connections

Run the connection test to verify everything is configured correctly:

```bash
cd backend
python scripts/test_connections.py
```

Expected output:
```
✓ Neo4j connection successful!
✓ OpenRouter response: Hello from OpenRouter!

TEST SUMMARY
Neo4j......................... ✓ PASS
OpenRouter.................... ✓ PASS
```

If tests fail, check:
- Network connectivity
- API keys are correct
- Neo4j database is running and accessible
- OpenRouter account has credits

## Step 4: Index Demo Papers

### Quick Start (20 papers, ~5-10 minutes)

```bash
python scripts/preindex_demo_papers.py --quick
```

This will index:
- 10 influential papers (Transformers, BERT, GPT-3, etc.)
- 10 recent papers across 3 popular topics

### Full Demo (100+ papers, ~30-60 minutes)

```bash
python scripts/preindex_demo_papers.py
```

This will index 100+ papers across 12 AI/ML topics:
- Large Language Models & Transformers
- Graph Neural Networks
- Retrieval Augmented Generation (RAG)
- Few-Shot Learning
- Reinforcement Learning
- Computer Vision
- Natural Language Processing
- Multimodal Learning
- Neural Architecture Search
- Explainable AI
- Contrastive Learning
- Attention Mechanisms

### Custom Topics

```bash
python scripts/preindex_demo_papers.py \
  --topics "transformers" "graph neural networks" "reinforcement learning" \
  --max-papers 50 \
  --categories cs.AI cs.LG
```

### Monitoring Progress

The script will show:
- Papers being downloaded
- Processing status
- Entities extracted
- Indexing progress
- Final summary with success/failure counts

## Step 5: Start the Application

### Backend Server

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

The server will start at: `http://localhost:8000`

API documentation: `http://localhost:8000/docs`

### Frontend (in a separate terminal)

```bash
cd frontend
npm install
npm run dev
```

The frontend will start at: `http://localhost:3000`

## Step 6: Using the Application

### Search for Papers

Navigate to the chat interface and try queries like:

- "What are the latest advances in graph neural networks?"
- "Compare attention mechanisms across different papers"
- "Find papers about retrieval augmented generation"
- "Show me papers that use BERT for NLP tasks"

### Explore the Graph

1. Go to the Graph page
2. Filter by entities, papers, or relationships
3. Click nodes to see details
4. Explore connections between papers

### Index More Papers

Use the ArXiv API endpoints:

```bash
# Search arXiv
curl -X POST http://localhost:8000/api/v1/arxiv/search \
  -H "Content-Type: application/json" \
  -d '{"query": "quantum computing", "max_results": 10}'

# Index specific papers
curl -X POST http://localhost:8000/api/v1/arxiv/bulk-index \
  -H "Content-Type: application/json" \
  -d '{"arxiv_ids": ["2301.00001", "2301.00002"]}'

# Index trending papers
curl -X POST http://localhost:8000/api/v1/arxiv/index-trending \
  -H "Content-Type: application/json" \
  -d '{
    "categories": ["cs.AI", "cs.LG"],
    "days_back": 7,
    "max_results": 50
  }'
```

## OpenRouter Models

You can use different models by changing the `OPENAI_MODEL` in `.env`:

```bash
# GPT-4 Turbo (recommended)
OPENAI_MODEL=openai/gpt-4-turbo-preview

# GPT-4
OPENAI_MODEL=openai/gpt-4

# GPT-3.5 Turbo (faster, cheaper)
OPENAI_MODEL=openai/gpt-3.5-turbo

# Claude (Anthropic)
OPENAI_MODEL=anthropic/claude-3-opus

# Llama 3 (Open source)
OPENAI_MODEL=meta-llama/llama-3-70b-instruct
```

See all available models at: https://openrouter.ai/models

## Troubleshooting

### Neo4j Connection Issues

```bash
# Test connection
python -c "
from neo4j import GraphDatabase
driver = GraphDatabase.driver(
    'neo4j+s://85da7327.databases.neo4j.io',
    auth=('neo4j', 'pcJR-Ag3HCFkHLCY2-_YdbvePns7w1ThoB34aozaGsw')
)
driver.verify_connectivity()
print('✓ Connected!')
driver.close()
"
```

If this fails:
- Check network/firewall settings
- Verify Neo4j Aura instance is running
- Check credentials are correct

### OpenRouter API Issues

```bash
# Test API key
curl https://openrouter.ai/api/v1/models \
  -H "Authorization: Bearer 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"
```

If this fails:
- Check API key is correct
- Verify account has credits
- Check you're not hitting rate limits

### Pinecone Connection Issues

```bash
# Test Pinecone
python -c "
from pinecone import Pinecone
pc = Pinecone(api_key='pcsk_5re6Dq_CUZ1oWcTPtUc2rVftcD2RuDPMwLwLhY3ubpnPiFy3nMBMoWPNff3h76stgtR9rM')
index = pc.Index('quickstart')
print(f'✓ Connected! Vectors: {index.describe_index_stats()}')
"
```

### PDF Download Issues

```bash
# Check download directory
mkdir -p data/arxiv_pdfs
ls -la data/arxiv_pdfs

# Check disk space
df -h
```

### Memory Issues

If processing fails due to memory:
- Reduce `MAX_CONCURRENT_PROCESSES` in `.env`
- Index fewer papers at once
- Increase available RAM

## Performance Tips

1. **Batch Processing**: Index papers in batches of 20-50
2. **Rate Limiting**: arXiv allows 3 requests/second (already configured)
3. **Caching**: LangCache will cache LLM responses (saves cost and time)
4. **Pinecone**: Use serverless tier for better scalability
5. **OpenRouter**: Use cheaper models (GPT-3.5) for testing

## Cost Estimates

For 100 papers:

- **OpenRouter (GPT-4 Turbo)**: ~$5-10 (entity extraction)
- **OpenRouter (GPT-3.5 Turbo)**: ~$0.50-1 (cheaper alternative)
- **Pinecone**: Free tier covers 100K vectors
- **Neo4j Aura**: Free tier covers small graphs
- **arXiv**: Free (no API key needed)
- **Firecrawl**: Free tier covers basic usage

Total: **$5-10 for GPT-4** or **$0.50-1 for GPT-3.5**

## Next Steps

After setup, you can:

1. **Explore**: Chat with papers, explore graph
2. **Index More**: Add papers on topics you care about
3. **Customize**: Adjust entity extraction prompts
4. **Enhance**: Add community detection (Phase 2)
5. **Deploy**: Set up production environment

## Support

For issues:
- Check logs: `tail -f backend/logs/*.log`
- Run tests: `python scripts/test_services.py`
- Verify config: `cat backend/.env`
- Check API docs: `http://localhost:8000/docs`

## Additional Resources

- [ArXiv API Docs](https://info.arxiv.org/help/api/index.html)
- [Neo4j Python Driver](https://neo4j.com/docs/python-manual/current/)
- [OpenRouter Docs](https://openrouter.ai/docs)
- [Pinecone Docs](https://docs.pinecone.io/)
- [FastAPI Docs](https://fastapi.tiangolo.com/)
