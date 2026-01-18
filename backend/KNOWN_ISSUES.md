# Known Issues and Workarounds

## Package Installation Issues

### ArXiv Library - sgmllib3k Dependency Issue

**Issue**: The `arxiv` package depends on `feedparser`, which in turn depends on `sgmllib3k`. On Python 3.11+, `sgmllib3k` may fail to build due to setuptools compatibility issues.

**Error**:
```
AttributeError: install_layout. Did you mean: 'install_platlib'?
ERROR: Failed building wheel for sgmllib3k
```

**Workarounds**:

1. **Use Pre-built Environment** (Recommended for Production):
   - Use Docker with Python 3.10 instead of 3.11
   - Or use a Python environment where sgmllib3k is pre-installed

2. **Manual Installation**:
   ```bash
   # Try installing sgmllib3k from a pre-built wheel
   pip install sgmllib3k==1.0.0 --prefer-binary

   # If that fails, try installing feedparser without dependencies
   pip install --no-deps feedparser
   # Then manually install sgmllib.py compatibility shim
   ```

3. **Skip ArXiv Features**:
   - The application will work without arXiv integration
   - ArXiv-related endpoints will return graceful errors
   - All other GraphRAG features remain functional

### Pinecone Client Version

**Issue**: The package was renamed from `pinecone-client` to `pinecone` in newer versions.

**Solution**: We use `pinecone-client==5.0.1` which is compatible with our code. The requirements.txt has been updated to reflect this.

## Deployment Recommendations

### Python Version
- **Recommended**: Python 3.10.x
- **Supported but with issues**: Python 3.11.x (sgmllib3k build issues)
- **Not tested**: Python 3.12+

### Docker Deployment (Recommended)
Using Docker avoids all package build issues:

```dockerfile
FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . /app
WORKDIR /app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Testing Installation

Run the service tests to verify everything is working:

```bash
cd backend
python scripts/test_services.py
```

This will test:
- ArXiv client (requires arxiv package)
- Pinecone vector store (requires pinecone-client)
- Firecrawl service (requires firecrawl-py)

## Runtime Environment Notes

### Sandbox/Restricted Environments
Some features require network access and may not work in sandbox environments:
- OpenRouter API calls
- Neo4j Aura cloud connections
- Pinecone vector operations
- ArXiv paper downloads
- Firecrawl web scraping

The application handles these gracefully and will log appropriate warnings.

### API Keys Required
Ensure all required API keys are set in `.env`:
- `OPENAI_API_KEY` or `OPENROUTER_API_KEY`
- `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`
- `PINECONE_API_KEY`
- `FIRECRAWL_API_KEY` (optional)

## CI/CD Notes

### Black Formatter
All Python code must be formatted with black:

```bash
cd backend
black app/ scripts/
```

This is enforced in GitHub Actions. Commits that don't pass formatting will fail CI.

### Pre-commit Hooks (Recommended)
Install pre-commit hooks to auto-format:

```bash
pip install pre-commit
pre-commit install
```

This will run black automatically before each commit.
