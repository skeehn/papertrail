# 📚 Papertrail

**GraphRAG-Powered Research Paper Analysis Platform**

Papertrail is an AI-powered research assistant that helps you discover insights across academic papers using advanced Graph Retrieval-Augmented Generation (GraphRAG), multi-hop reasoning, and trend analysis.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Next.js 15](https://img.shields.io/badge/Next.js-15-black)](https://nextjs.org/)

[Live Demo](https://papertrail-demo.vercel.app) · [Documentation](./docs) · [Report Bug](https://github.com/skeehn/papertrail/issues) · [Request Feature](https://github.com/skeehn/papertrail/issues)

---

## ✨ Features

### 🔍 Intelligent Search & Discovery
- **Hybrid Search**: Combines vector similarity (Pinecone) + graph traversal (Neo4j)
- **Multi-Hop Reasoning**: Answer complex questions requiring multiple reasoning steps
- **Semantic Search**: Find papers by meaning, not just keywords

### 📊 Research Analytics
- **Trend Detection**: Track how research topics evolve over time
- **Community Detection**: Auto-identify research clusters and topics
- **Emerging Topics**: Discover fast-growing research areas
- **Citation Analysis**: Build and explore citation networks

### 🤖 Multi-Agent AI System
- **Synthesizer Agent**: Summarize papers and extract key findings
- **Critic Agent**: Identify assumptions and contradictions
- **Connector Agent**: Find relationships across papers
- **Reasoning Agent**: Multi-step question answering

### 📈 Knowledge Graph
- **Neo4j Graph Database**: Rich entity-relationship modeling
- **Entity Extraction**: Automatically extract methods, datasets, findings
- **Relationship Detection**: Discover connections between concepts
- **Graph Visualization**: Interactive exploration of research landscape

### 🚀 ArXiv Integration
- **Automatic Paper Discovery**: Search arXiv by topic, category, author
- **Bulk Indexing**: Process hundreds of papers efficiently
- **Metadata Enrichment**: Complete paper information extraction
- **Trending Papers**: Track recent publications in your field

---

## 🎯 Use Cases

**For Researchers**:
- "What methods from sentiment analysis also appear in summarization research?"
- "How have transformer architectures evolved from 2017 to 2024?"
- "Which datasets are commonly used for few-shot learning?"

**For Literature Review**:
- Automatically organize papers by topic
- Find research gaps and understudied areas
- Track methodological trends over time
- Identify seminal papers in a field

**For Learning**:
- Understand complex research topics through multi-hop reasoning
- Discover connections between different subfields
- Follow the evolution of ideas across papers

---

## 🏗️ Architecture

```
┌─────────────┐
│   Next.js   │  Frontend (React 18, Tailwind, shadcn/ui)
│  Frontend   │
└──────┬──────┘
       │
       ↓ HTTP/WebSocket
┌─────────────┐
│   FastAPI   │  Backend (Python, OpenAI, LangChain)
│   Backend   │
└──────┬──────┘
       │
       ├─────→ Neo4j (Knowledge Graph)
       ├─────→ Pinecone (Vector Search)
       ├─────→ OpenRouter (LLM APIs)
       └─────→ ArXiv (Paper Source)
```

**Tech Stack**:
- **Frontend**: Next.js 15, React 18, TypeScript, Tailwind CSS
- **Backend**: FastAPI, Python 3.11+, OpenAI SDK
- **Databases**: Neo4j (graph), Pinecone (vectors)
- **AI**: OpenRouter (GPT-4, Claude, Llama), SentenceTransformers
- **Processing**: ArXiv API, PyMuPDF, LangChain

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Neo4j Aura account (free tier)
- Pinecone account (free tier)
- OpenRouter API key

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/skeehn/papertrail.git
   cd papertrail
   ```

2. **Install dependencies**
   ```bash
   # Backend
   cd backend
   pip install -r requirements.txt

   # Frontend
   cd ../frontend
   npm install
   ```

3. **Configure environment**
   ```bash
   # Frontend
   cp frontend/.env.local.example frontend/.env.local
   # Edit frontend/.env.local with your backend URL (default: http://localhost:8000)

   # Backend (optional)
   cp backend/.env.example backend/.env
   # Edit backend/.env with your API keys (OpenRouter, Neo4j, Pinecone)
   ```

4. **Test connections** (optional - requires configured backend)
   ```bash
   cd backend
   python scripts/test_connections.py
   ```

5. **Start the application**

   Option A: Start Frontend Only (uses mock backend data)
   ```bash
   cd frontend
   npm run dev
   # Frontend will start at: http://localhost:3000
   ```

   Option B: Start Backend (requires Neo4j and API keys)
   ```bash
   # Backend (terminal 1)
   cd backend
   uvicorn app.main:app --reload --port 8000

   # Frontend (in a separate terminal)
   cd frontend
   npm run dev
   # Frontend will start at: http://localhost:3000
   # API docs at: http://localhost:8000/docs
   ```

### ✅ Recently Completed (This Integration Plan)

**Phase 1 - Core Connectivity:**
- ✅ Removed hardcoded paths and debug code from `papers.py`
- ✅ Created Next.js API route proxies for papers, agents, and dashboard
- ✅ Connected Papers Library to real API with `use-papers` hook
- ✅ Connected Enhanced Chat to backend agents with `use-agent-chat` hook
- ✅ Connected Dashboard to real APIs

**Phase 2 - Graph Enhancement:**
- ✅ Implemented real Neo4j queries in graph endpoints
- ✅ Created force-directed graph layout utility
- ✅ Added interactive features (layout selector, export button)

**Phase 3 - Testing & Caching:**
- ✅ Added backend tests for papers, agents, and graph endpoints
- ✅ Created basic in-memory cache with TTL and cleanup

**Phase 4 - New Features:**
- ✅ Citation network analysis service and API
- ✅ Contradiction detection service and API
- ✅ Research gap analysis service and API
- ✅ Paper recommendations service and API

### ⚠️ Known Issues & Next Steps

**Backend Issues:**
- Neo4j connection required for graph features (currently uses mock fallback)
- ArXiv library optional dependency
- LSP type warnings in some endpoints (non-blocking)

**Frontend Issues:**
- Requires `BACKEND_URL` in `.env.local` for API calls
- Components use API routes that proxy to backend

**To Get Fully Working:**

1. **Configure Environment:**
   ```bash
   cd frontend
   cp .env.local.example .env.local
   # Edit .env.local: BACKEND_URL=http://localhost:8000
   ```

2. **Install ArXiv Library (optional):**
   ```bash
   cd backend
   pip install arxiv
   ```

3. **Start Backend with API Keys:**
   - Add OpenRouter or OpenAI API key to `.env`
   - Optionally configure Neo4j for graph features
   - Run: `uvicorn app.main:app --reload --port 8000`

4. **Start Frontend:**
   ```bash
   cd frontend
   npm run dev
   ```

5. **Test Integration:**
   - Upload a paper via chat
   - Check Papers Library page
   - Try graph visualization
   - Use agent chat with different agent types

6. **Start the application**
   ```bash
   # Backend (terminal 1)
   cd backend
   uvicorn app.main:app --reload --port 8000

   # Frontend (terminal 2)
   cd frontend
   npm run dev
   ```

7. **Open in browser**: http://localhost:3000

---

## 📖 Documentation

- **[Setup Guide](./SETUP_GUIDE.md)** - Detailed installation and configuration
- **[Deployment Guide](./DEPLOYMENT.md)** - Deploy to Vercel, Railway, Docker
- **[ArXiv Integration](./ARXIV_INTEGRATION.md)** - ArXiv features and usage
- **[API Documentation](http://localhost:8000/docs)** - Interactive API docs (when running)

---

## 🎮 Usage Examples

### Chat with Papers

```bash
# Ask complex questions
"What are the key differences between BERT and GPT-3?"

# Multi-hop reasoning
"What methods used in NLP also appear in computer vision, and how do they compare?"

# Trend analysis
"How has the use of attention mechanisms grown from 2017 to 2024?"
```

### API Usage

```python
import requests

# Search arXiv
papers = requests.post(
    "http://localhost:8000/api/v1/arxiv/search",
    json={"query": "graph neural networks", "max_results": 10}
).json()

# Detect communities
communities = requests.post(
    "http://localhost:8000/api/v1/communities/detect",
    json={"algorithm": "louvain", "min_community_size": 3}
).json()

# Get trending topics
trending = requests.get(
    "http://localhost:8000/api/v1/insights/trends/trending?recent_months=6"
).json()

# Complex reasoning
answer = requests.post(
    "http://localhost:8000/api/v1/insights/reasoning",
    json={"query": "What datasets are best for few-shot learning?"}
).json()
```

### Index Custom Papers

```bash
# Index specific papers
python scripts/preindex_demo_papers.py \
  --topics "quantum computing" "blockchain" \
  --max-papers 50

# Index by arXiv category
curl -X POST http://localhost:8000/api/v1/arxiv/index-trending \
  -H "Content-Type: application/json" \
  -d '{
    "categories": ["cs.AI", "cs.LG"],
    "days_back": 7,
    "max_results": 100
  }'
```

---

## 🌟 Key Features in Detail

### GraphRAG System

Traditional RAG retrieves documents by similarity. Papertrail's **GraphRAG** understands relationships:

```
Question: "What methods from NLP are used in computer vision?"

Traditional RAG:
1. Find papers about "NLP methods"
2. Find papers about "computer vision"
3. Return results

Papertrail GraphRAG:
1. Find NLP methods (BERT, Transformer, Attention)
2. Traverse graph to find papers using these in CV
3. Analyze relationships and success rates
4. Synthesize insights across multiple hops
```

### Community Detection

Automatically clusters research into topics:

```
Input: 100 papers on AI

Output:
- Community 1: "Large Language Models" (23 papers)
- Community 2: "Graph Neural Networks" (18 papers)
- Community 3: "Few-Shot Learning" (15 papers)
- Community 4: "Computer Vision" (22 papers)
- Community 5: "Reinforcement Learning" (12 papers)

Each with auto-generated summary and key papers.
```

### Multi-Hop Reasoning

Break complex questions into steps:

```
Query: "How have transformer architectures evolved, and which
       datasets are they most commonly tested on?"

Step 1: Find early transformer papers (2017-2019)
Step 2: Find recent transformer papers (2020-2024)
Step 3: Extract architecture changes
Step 4: Identify evaluation datasets
Step 5: Synthesize evolution timeline + dataset preferences

Answer: "Transformers evolved from basic attention (Vaswani 2017)
        to BERT's bidirectional encoding (2018) to GPT's generative
        approach (2019+). Modern transformers like GPT-4 and Llama 3
        scale to billions of parameters. Most commonly tested on
        GLUE (NLP), ImageNet (vision), and WMT (translation)."
```

---

## 🛠️ Development

### Project Structure

```
papertrail/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/     # API routes
│   │   ├── agents/               # Multi-agent system
│   │   ├── services/             # Business logic
│   │   ├── database/             # Neo4j, Pinecone clients
│   │   └── core/                 # Config, logging
│   ├── scripts/                  # Utility scripts
│   └── tests/                    # Tests
├── frontend/
│   ├── src/
│   │   ├── app/                  # Next.js pages
│   │   ├── components/           # React components
│   │   └── services/             # API clients
│   └── public/                   # Static assets
└── docs/                         # Documentation
```

### Running Tests

```bash
# Backend
cd backend
pytest

# Frontend
cd frontend
npm test

# E2E
npm run test:e2e
```

### Contributing

We welcome contributions! Please see [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📊 Performance

**Processing Speed**:
- Single paper: ~30-60 seconds
- 100 papers batch: ~30-60 minutes
- Complex query: ~5-15 seconds

**Scalability**:
- Papers: Tested up to 10,000+ papers
- Concurrent users: Scales with backend instances
- Vector search: Millisecond latency (Pinecone serverless)

**Cost** (for 100 papers):
- GPT-4 Turbo: ~$5-10
- GPT-3.5 Turbo: ~$0.50-1
- Pinecone: Free tier covers 100K vectors
- Neo4j Aura: Free tier covers small graphs

---

## 🔐 Security

- API keys stored in environment variables
- Neo4j uses SSL/TLS (neo4j+s://)
- CORS configured for production domains
- Rate limiting on all endpoints
- Input validation and sanitization

---

## 🗺️ Roadmap

- [x] Phase 1: ArXiv integration + basic GraphRAG
- [x] Phase 2: Community detection + multi-hop reasoning + trends
- [ ] Phase 3: Citation networks + contradiction detection
- [ ] Phase 4: Research gap analysis + paper recommendations
- [ ] Phase 5: Real-time collaboration + team features
- [ ] Phase 6: Custom datasets (beyond arXiv)

---

## 💡 Alternative Use Cases

Papertrail's architecture can be adapted for other domains:

**Medical Research**: PubMed papers, clinical trials, drug interactions
**Legal Research**: Case law, statutes, precedents
**Business Intelligence**: Market research, competitor analysis
**News Analysis**: Investigative journalism, fact-checking
**Open Data**: Government documents, FOIA requests, public records

The core GraphRAG system works with any corpus of documents.

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [Neo4j](https://neo4j.com/) for graph database
- [Pinecone](https://www.pinecone.io/) for vector search
- [OpenRouter](https://openrouter.ai/) for LLM API access
- [ArXiv](https://arxiv.org/) for research paper access
- [LangChain](https://www.langchain.com/) for AI frameworks
- [Vercel](https://vercel.com/) for deployment platform

---

## 📧 Contact

**Created by**: [@skeehn](https://github.com/skeehn)

**Project Link**: [https://github.com/skeehn/papertrail](https://github.com/skeehn/papertrail)

**Issues**: [https://github.com/skeehn/papertrail/issues](https://github.com/skeehn/papertrail/issues)

---

## ⭐ Star History

If you find Papertrail useful, please consider starring the repository!

---

Built with ❤️ for researchers, by researchers.
