# Quick Test Instructions

## Start Services

### Backend
```bash
cd backend
# Set your OpenRouter API key in .env
echo "OPENAI_API_KEY=sk-or-v1-your-key-here" >> .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend
```bash
cd frontend
npm run dev
```

## Test Checklist

### ✅ 1. OpenRouter Chat Test
1. Open http://localhost:3000
2. Go to chat interface
3. Select "Synthesizer" agent
4. Type: "Explain quantum computing in simple terms"
5. **Expected:** Response appears with typing animation, copy button on hover

### ✅ 2. Document Upload Test
1. In chat interface, drag a PDF file to upload area
2. Click "Upload" button
3. **Expected:** 
   - Progress bar animates
   - WebSocket updates show processing steps
   - Success message appears
   - Paper appears in library

### ✅ 3. Search Test
1. Go to Papers Library page
2. Type in search bar (e.g., "machine learning")
3. **Expected:**
   - Autocomplete suggestions appear
   - Results highlight search terms
   - Tag filters work
   - Results animate in

### ✅ 4. All Agent Types Test
Test each agent:
- **Synthesizer:** "Summarize the key points of transformer architecture"
- **Critic:** "What are the limitations of current LLMs?"
- **Connector:** "How do attention mechanisms relate to memory?"
- **Reasoning:** "If neural networks can approximate any function, what are the practical constraints?"

### ✅ 5. UI Polish Check
- [ ] Smooth animations on all interactions
- [ ] Hover effects on cards
- [ ] Loading skeletons appear
- [ ] Error states are clear
- [ ] Copy buttons work
- [ ] Message feedback works

## API Endpoint Tests

```bash
# Test chat
curl -X POST http://localhost:8000/api/v1/agents/query \
  -H "Content-Type: application/json" \
  -d '{"agent_type": "synthesizer", "query": "Hello", "paper_ids": []}'

# Test papers
curl http://localhost:8000/api/v1/papers/

# Test graph
curl http://localhost:8000/api/v1/graph/statistics
```

## Troubleshooting

- **Chat not responding:** Check OpenRouter API key in backend/.env
- **Upload fails:** Check file size < 50MB, PDF format
- **WebSocket errors:** Check NEXT_PUBLIC_WS_URL in frontend/.env.local
- **Search empty:** Upload papers first, then search
