# PaperTrail Testing Guide

## Quick Start Testing

### Prerequisites
1. Backend server running on `http://localhost:8000`
2. Frontend server running on `http://localhost:3000`
3. OpenRouter API key set in `backend/.env`:
   ```
   OPENAI_API_KEY=sk-or-v1-...
   OPENAI_BASE_URL=https://openrouter.ai/api/v1
   OPENAI_MODEL=openai/gpt-4-turbo
   ```

### Manual Testing Checklist

#### 1. OpenRouter Configuration ✅
- [x] Backend config defaults to OpenRouter URL
- [x] OpenRouter headers configured (HTTP-Referer, X-Title)
- [x] Model format set to OpenRouter style (`openai/gpt-4-turbo`)

**Test:** Check backend logs when starting - should show OpenRouter base URL

#### 2. Chat Functionality ✅
**Location:** Main chat interface (`/` or chat page)

**Tests:**
- [ ] Select "Synthesizer" agent and ask: "What is machine learning?"
- [ ] Select "Critic" agent and ask: "Critique this claim: AI will replace all jobs"
- [ ] Select "Connector" agent and ask: "How does deep learning relate to neural networks?"
- [ ] Select "Reasoning" agent and ask: "If A causes B, and B causes C, what can we infer about A and C?"

**Expected:**
- Agent selector shows icons and descriptions
- Messages animate in smoothly
- Typing indicators appear while loading
- Copy button appears on hover for assistant messages
- Thumbs up/down buttons work
- Error states show retry button

#### 3. Document Upload & Processing ✅
**Location:** Chat interface upload area

**Tests:**
- [ ] Drag and drop a PDF file
- [ ] Click upload area to browse for PDF
- [ ] Upload a test PDF (max 50MB)
- [ ] Watch processing progress via WebSocket
- [ ] Verify paper appears in library after processing

**Expected:**
- Drag zone highlights when dragging file
- Upload progress bar animates
- Processing steps show: "Extracting text" → "Extracting entities" → "Building graph" → "Indexing"
- Success animation with checkmark
- WebSocket updates appear in real-time
- Paper appears in `/papers` page after completion

#### 4. Search Functionality ✅
**Location:** Papers Library (`/papers`)

**Tests:**
- [ ] Type in search bar - autocomplete suggestions appear
- [ ] Click a suggestion to auto-fill search
- [ ] Search highlights matching terms in results
- [ ] Filter by tags - click tag buttons
- [ ] Clear search with X button
- [ ] Switch between grid and list view
- [ ] Verify results count displays correctly

**Expected:**
- Autocomplete dropdown appears after 2+ characters
- Search terms highlighted in yellow
- Tag filters toggle on/off
- Results animate in with stagger effect
- Empty state shows helpful message

#### 5. UI/UX Enhancements ✅
**Visual Checks:**
- [ ] Smooth page transitions
- [ ] Loading skeletons appear during data fetch
- [ ] Hover effects on cards (lift, shadow)
- [ ] Button hover states work
- [ ] Custom scrollbar styling visible
- [ ] Gradient backgrounds on icons
- [ ] Animations are smooth (60fps)

**Interaction Checks:**
- [ ] Keyboard shortcuts work (Enter to send, Shift+Enter for new line)
- [ ] Copy-to-clipboard works for messages
- [ ] Message feedback (thumbs) persists during session
- [ ] Error messages are clear and actionable
- [ ] Retry buttons work correctly

### Automated Testing

Run the integration test script:
```bash
./test_integration.sh
```

Or test individual endpoints:

```bash
# Test chat
curl -X POST http://localhost:8000/api/v1/agents/query \
  -H "Content-Type: application/json" \
  -d '{"agent_type": "synthesizer", "query": "Hello", "paper_ids": []}'

# Test papers list
curl http://localhost:8000/api/v1/papers/

# Test graph stats
curl http://localhost:8000/api/v1/graph/statistics
```

### Common Issues & Solutions

1. **OpenRouter API errors:**
   - Check `OPENAI_API_KEY` is set correctly
   - Verify API key has credits
   - Check model name is correct (`openai/gpt-4-turbo`)

2. **WebSocket not connecting:**
   - Check backend WebSocket endpoint is enabled
   - Verify `NEXT_PUBLIC_WS_URL` in frontend `.env`
   - Check browser console for connection errors

3. **Upload fails:**
   - Check file is PDF and under 50MB
   - Verify backend upload directory exists
   - Check backend logs for processing errors

4. **Search not working:**
   - Verify papers are indexed
   - Check frontend API proxy routes
   - Verify backend search endpoint responds

### Performance Checks

- Chat response time: < 5 seconds
- Upload processing: < 30 seconds for typical PDF
- Search results: < 1 second
- UI animations: Smooth, no jank

### Browser Testing

Test in:
- [ ] Chrome/Edge (Chromium)
- [ ] Firefox
- [ ] Safari
- [ ] Mobile viewport (responsive)

### Accessibility Checks

- [ ] Keyboard navigation works
- [ ] Screen reader compatible
- [ ] Focus indicators visible
- [ ] Color contrast sufficient
- [ ] ARIA labels present
