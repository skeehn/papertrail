# Papertrail Deployment Guide

Complete guide for deploying Papertrail to production.

## Deployment Options

### Option 1: Vercel (Frontend) + Railway/Render (Backend)

**Best for**: Quick deployment, automatic scaling, minimal configuration

#### Frontend (Vercel)

1. **Connect Repository**
   ```bash
   # Push your code to GitHub
   git push origin main

   # Go to vercel.com and import your repository
   ```

2. **Configure Build Settings**
   - Framework Preset: Next.js
   - Root Directory: `frontend`
   - Build Command: `npm run build`
   - Output Directory: `.next`

3. **Environment Variables**
   ```
   NEXT_PUBLIC_API_URL=https://your-api.railway.app
   NEXT_PUBLIC_APP_NAME=Papertrail
   ```

4. **Deploy**
   - Click "Deploy"
   - Vercel will automatically build and deploy your frontend

#### Backend (Railway)

1. **Create New Project**
   - Go to railway.app
   - Click "New Project" → "Deploy from GitHub repo"
   - Select your repository

2. **Configure Service**
   - Root Directory: `backend`
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

3. **Environment Variables**
   ```
   # Neo4j
   NEO4J_URI=neo4j+s://85da7327.databases.neo4j.io
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=pcJR-Ag3HCFkHLCY2-_YdbvePns7w1ThoB34aozaGsw
   NEO4J_DATABASE=neo4j

   # OpenRouter
   OPENAI_API_KEY=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
   OPENAI_BASE_URL=https://openrouter.ai/api/v1
   OPENAI_MODEL=openai/gpt-4-turbo-preview

   # Pinecone
   PINECONE_API_KEY=pcsk_5re6Dq_CUZ1oWcTPtUc2rVftcD2RuDPMwLwLhY3ubpnPiFy3nMBMoWPNff3h76stgtR9rM
   PINECONE_INDEX_NAME=quickstart

   # Firecrawl (optional)
   FIRECRAWL_API_KEY=fc-d847c9daa2714f7f9a26d440a86a7695
   FIRECRAWL_ENABLED=true

   # App Config
   ENVIRONMENT=production
   DEBUG=false
   MAX_CONCURRENT_PROCESSES=4
   ARXIV_DOWNLOAD_DIR=/tmp/arxiv_pdfs
   ```

4. **Generate Domain**
   - Railway will provide a domain like `https://papertrail-production.up.railway.app`
   - Use this URL in your frontend's `NEXT_PUBLIC_API_URL`

5. **Deploy**
   - Railway auto-deploys on every push to main

---

### Option 2: Docker Compose (Self-Hosted)

**Best for**: Full control, custom infrastructure, cost optimization

1. **Create docker-compose.yml**
   ```yaml
   version: '3.8'

   services:
     frontend:
       build:
         context: ./frontend
         dockerfile: Dockerfile
       ports:
         - "3000:3000"
       environment:
         - NEXT_PUBLIC_API_URL=http://backend:8000
       depends_on:
         - backend

     backend:
       build:
         context: ./backend
         dockerfile: Dockerfile
       ports:
         - "8000:8000"
       environment:
         - NEO4J_URI=${NEO4J_URI}
         - NEO4J_USER=${NEO4J_USER}
         - NEO4J_PASSWORD=${NEO4J_PASSWORD}
         - OPENAI_API_KEY=${OPENAI_API_KEY}
         - OPENAI_BASE_URL=${OPENAI_BASE_URL}
         - PINECONE_API_KEY=${PINECONE_API_KEY}
       volumes:
         - ./data:/app/data
   ```

2. **Create Backend Dockerfile**
   ```dockerfile
   # backend/Dockerfile
   FROM python:3.11-slim

   WORKDIR /app

   # Install dependencies
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt

   # Copy application
   COPY . .

   # Create data directories
   RUN mkdir -p /app/data/arxiv_pdfs

   # Run application
   CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
   ```

3. **Create Frontend Dockerfile**
   ```dockerfile
   # frontend/Dockerfile
   FROM node:18-alpine

   WORKDIR /app

   # Install dependencies
   COPY package*.json ./
   RUN npm ci

   # Copy application
   COPY . .

   # Build
   RUN npm run build

   # Run
   CMD ["npm", "start"]
   ```

4. **Deploy**
   ```bash
   # Set environment variables
   cp .env.example .env
   # Edit .env with your credentials

   # Build and start
   docker-compose up -d

   # View logs
   docker-compose logs -f

   # Stop
   docker-compose down
   ```

---

### Option 3: Kubernetes (Enterprise)

**Best for**: Large scale, high availability, multi-region

See `k8s/` directory for Kubernetes manifests.

---

## Pre-Deployment Checklist

### 1. Environment Variables

Ensure all required variables are set:

- [ ] NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
- [ ] OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL
- [ ] PINECONE_API_KEY, PINECONE_INDEX_NAME
- [ ] FIRECRAWL_API_KEY (optional)

### 2. Database Setup

- [ ] Neo4j Aura database is running and accessible
- [ ] Pinecone index "quickstart" is created (dimension: 384)
- [ ] Test connections using `python backend/scripts/test_connections.py`

### 3. Data Preparation

- [ ] Pre-index demo papers: `python backend/scripts/preindex_demo_papers.py --quick`
- [ ] Verify papers are in database
- [ ] Run community detection: `POST /api/v1/communities/detect`

### 4. Security

- [ ] Change all default passwords
- [ ] Use strong SECRET_KEY for JWT
- [ ] Enable HTTPS in production
- [ ] Set CORS_ORIGINS to your domain only
- [ ] Disable DEBUG mode in production

### 5. Performance

- [ ] Enable caching (Redis/LangCache)
- [ ] Set reasonable rate limits
- [ ] Configure CDN for static assets (Vercel handles this)
- [ ] Enable gzip compression

---

## Post-Deployment

### 1. Health Checks

**Backend Health**:
```bash
curl https://your-api-url.com/health
# Expected: {"status": "healthy"}
```

**Database Connection**:
```bash
curl https://your-api-url.com/api/v1/graph/statistics
# Expected: Graph stats with node/relationship counts
```

### 2. Monitoring

Set up monitoring for:
- API response times
- Error rates
- Database connection pool
- LLM API costs (OpenRouter usage)
- Vector store operations (Pinecone)

Recommended tools:
- Sentry for error tracking
- Vercel Analytics (built-in for frontend)
- Railway Metrics (built-in for backend)

### 3. Indexing Schedule

Set up a cron job to index new papers:

```bash
# Daily at 2 AM: Index trending AI papers
0 2 * * * curl -X POST https://your-api-url.com/api/v1/arxiv/index-trending \
  -H "Content-Type: application/json" \
  -d '{"categories": ["cs.AI", "cs.LG"], "days_back": 1, "max_results": 20}'
```

### 4. Community Detection

Run weekly:

```bash
# Every Sunday at 3 AM: Detect new research communities
0 3 * * 0 curl -X POST https://your-api-url.com/api/v1/communities/detect \
  -H "Content-Type: application/json" \
  -d '{"algorithm": "louvain", "min_community_size": 3}'
```

---

## Scaling

### Frontend Scaling

Vercel handles this automatically with:
- Edge caching
- Global CDN
- Automatic scaling

### Backend Scaling

**Railway/Render**:
- Upgrade plan for more CPU/RAM
- Enable autoscaling (Pro plan)

**Docker/K8s**:
- Increase replica count
- Add horizontal pod autoscaler
- Use load balancer

**Database Scaling**:
- Neo4j Aura: Upgrade to larger instance
- Pinecone: Upgrade to higher tier
- Consider read replicas for Neo4j

### Cost Optimization

**Reduce LLM costs**:
```bash
# Use cheaper model
OPENAI_MODEL=openai/gpt-3.5-turbo  # ~10x cheaper

# Enable caching
LANGCACHE_ENABLED=true

# Reduce concurrent processes
MAX_CONCURRENT_PROCESSES=2
```

**Reduce compute costs**:
- Use smaller instance during low traffic
- Enable autoscaling to scale down
- Cache API responses aggressively

---

## Troubleshooting

### Issue: Frontend can't reach backend

**Solution**:
1. Check NEXT_PUBLIC_API_URL is set correctly
2. Verify backend is running: `curl https://your-api-url.com/health`
3. Check CORS settings in backend allow frontend domain

### Issue: Neo4j connection timeout

**Solution**:
1. Verify NEO4J_URI uses `neo4j+s://` for cloud
2. Check firewall allows outbound connections
3. Test connection: `python backend/scripts/test_connections.py`

### Issue: High OpenRouter costs

**Solution**:
1. Enable LangCache for semantic caching
2. Switch to cheaper model (GPT-3.5)
3. Reduce entity extraction chunk size
4. Limit concurrent processes

### Issue: Slow API responses

**Solution**:
1. Enable response caching
2. Optimize Neo4j queries (add indexes)
3. Use Pinecone serverless tier
4. Implement request queuing for heavy operations

---

## Maintenance

### Weekly Tasks

- [ ] Check error logs
- [ ] Review API usage and costs
- [ ] Update trending papers
- [ ] Run community detection

### Monthly Tasks

- [ ] Update dependencies
- [ ] Review and optimize database indexes
- [ ] Analyze performance metrics
- [ ] Review and adjust rate limits

### Quarterly Tasks

- [ ] Security audit
- [ ] Performance optimization review
- [ ] Cost optimization review
- [ ] User feedback incorporation

---

## Rollback Procedure

If deployment fails:

1. **Vercel**: Click "Rollback" to previous deployment
2. **Railway**: Revert to previous deployment in dashboard
3. **Docker**: `docker-compose down && git checkout previous-tag && docker-compose up -d`

Always test in staging before deploying to production!

---

## Support

For deployment issues:
- Check logs first
- Review this guide
- Search GitHub issues
- Open new issue with deployment details

---

## Next Steps

After successful deployment:
1. Share your deployment URL on Twitter/X
2. Gather user feedback
3. Monitor usage patterns
4. Plan feature additions based on feedback
5. Consider alternative datasets (e.g., specific research domains)

Your Papertrail instance is now live! 🎉
