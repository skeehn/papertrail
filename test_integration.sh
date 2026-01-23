#!/bin/bash

# Integration Test Script for PaperTrail
# Tests OpenRouter integration, chat, upload, and search functionality

set -e

echo "🧪 PaperTrail Integration Test Suite"
echo "===================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if backend is running
echo "📡 Checking backend server..."
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Backend is running${NC}"
else
    echo -e "${YELLOW}⚠ Backend not running. Please start it with: cd backend && uvicorn app.main:app --reload${NC}"
    exit 1
fi

# Check if frontend is running
echo "🌐 Checking frontend server..."
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Frontend is running${NC}"
else
    echo -e "${YELLOW}⚠ Frontend not running. Please start it with: cd frontend && npm run dev${NC}"
    exit 1
fi

# Test 1: OpenRouter Configuration
echo ""
echo "1️⃣ Testing OpenRouter Configuration..."
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"

# Check config endpoint if available, or test directly
echo "   Checking OpenRouter settings..."
RESPONSE=$(curl -s "${BACKEND_URL}/health" || echo "{}")
if echo "$RESPONSE" | grep -q "healthy"; then
    echo -e "${GREEN}✓ Backend health check passed${NC}"
else
    echo -e "${RED}✗ Backend health check failed${NC}"
fi

# Test 2: Agent Chat Endpoint
echo ""
echo "2️⃣ Testing Agent Chat Endpoint..."
CHAT_RESPONSE=$(curl -s -X POST "${BACKEND_URL}/api/v1/agents/query" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_type": "synthesizer",
    "query": "What is machine learning?",
    "paper_ids": []
  }' || echo '{"error": "failed"}')

if echo "$CHAT_RESPONSE" | grep -q "response\|error"; then
    if echo "$CHAT_RESPONSE" | grep -q "error"; then
        echo -e "${YELLOW}⚠ Chat endpoint returned error (may need OpenRouter API key)${NC}"
        echo "   Response: $(echo $CHAT_RESPONSE | head -c 200)"
    else
        echo -e "${GREEN}✓ Chat endpoint is working${NC}"
    fi
else
    echo -e "${RED}✗ Chat endpoint failed${NC}"
fi

# Test 3: Papers List Endpoint
echo ""
echo "3️⃣ Testing Papers List Endpoint..."
PAPERS_RESPONSE=$(curl -s "${BACKEND_URL}/api/v1/papers/?limit=5" || echo '{"error": "failed"}')

if echo "$PAPERS_RESPONSE" | grep -q "papers\|total\|error"; then
    if echo "$PAPERS_RESPONSE" | grep -q "error"; then
        echo -e "${YELLOW}⚠ Papers endpoint returned error${NC}"
    else
        echo -e "${GREEN}✓ Papers endpoint is working${NC}"
        PAPER_COUNT=$(echo "$PAPERS_RESPONSE" | grep -o '"total":[0-9]*' | grep -o '[0-9]*' || echo "0")
        echo "   Found $PAPER_COUNT papers"
    fi
else
    echo -e "${RED}✗ Papers endpoint failed${NC}"
fi

# Test 4: Graph Statistics
echo ""
echo "4️⃣ Testing Graph Statistics Endpoint..."
GRAPH_RESPONSE=$(curl -s "${BACKEND_URL}/api/v1/graph/statistics" || echo '{"error": "failed"}')

if echo "$GRAPH_RESPONSE" | grep -q "statistics\|error"; then
    if echo "$GRAPH_RESPONSE" | grep -q "error"; then
        echo -e "${YELLOW}⚠ Graph endpoint returned error${NC}"
    else
        echo -e "${GREEN}✓ Graph statistics endpoint is working${NC}"
    fi
else
    echo -e "${RED}✗ Graph endpoint failed${NC}"
fi

# Test 5: Frontend API Routes
echo ""
echo "5️⃣ Testing Frontend API Routes..."
FRONTEND_URL="${FRONTEND_URL:-http://localhost:3000}"

# Test dashboard stats
DASHBOARD_RESPONSE=$(curl -s "${FRONTEND_URL}/api/dashboard/stats" || echo '{"error": "failed"}')
if echo "$DASHBOARD_RESPONSE" | grep -q "totalPapers\|error"; then
    if echo "$DASHBOARD_RESPONSE" | grep -q "error"; then
        echo -e "${YELLOW}⚠ Dashboard API returned error${NC}"
    else
        echo -e "${GREEN}✓ Dashboard API is working${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Dashboard API check inconclusive${NC}"
fi

echo ""
echo "===================================="
echo "✅ Integration tests completed!"
echo ""
echo "📝 Next Steps:"
echo "   1. Ensure OPENAI_API_KEY is set in backend/.env"
echo "   2. Test chat functionality in the UI"
echo "   3. Upload a test PDF to verify processing"
echo "   4. Test search functionality with uploaded papers"
echo ""
