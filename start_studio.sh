#!/bin/bash

# LangGraph Studio Startup Script
# This script sets up and starts the LangGraph Studio for Order Analysis testing

set -e

echo "🚀 Starting LangGraph Studio for Order Analysis..."

# Check if uv is available
if ! command -v uv &> /dev/null; then
    echo "❌ uv not found. Please install uv first:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
else
    echo "✅ uv found"
fi

# Sync dependencies first
echo "📦 Syncing dependencies with uv..."
uv sync

# Check if langgraph-cli is installed
if ! uv run which langgraph &> /dev/null; then
    echo "❌ LangGraph CLI not found. Installing..."
    uv add langgraph-cli
else
    echo "✅ LangGraph CLI found"
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found. Please create one based on the example:"
    echo "   Required variables:"
    echo "   - GOOGLE_CLOUD_PROJECT"
    echo "   - LANGCHAIN_API_KEY"
    echo "   - LANGCHAIN_PROJECT"
    exit 1
else
    echo "✅ .env file found"
fi

# Check if requirements are installed
echo "📦 Checking dependencies..."
uv run python -c "import langgraph, langchain_google_vertexai, pydantic" 2>/dev/null && echo "✅ Core dependencies installed" || {
    echo "📦 Dependencies missing, already synced with uv"
}

# Validate environment variables
echo "🔧 Validating environment..."
source .env

if [ -z "$GOOGLE_CLOUD_PROJECT" ]; then
    echo "❌ GOOGLE_CLOUD_PROJECT not set in .env"
    exit 1
fi

if [ -z "$LANGCHAIN_API_KEY" ]; then
    echo "❌ LANGCHAIN_API_KEY not set in .env"
    exit 1
fi

echo "✅ Environment validated"

# Check Google Cloud authentication
echo "🔐 Checking Google Cloud authentication..."
if ! gcloud auth application-default print-access-token &> /dev/null; then
    echo "⚠️  Google Cloud authentication not set up"
    echo "   Run: gcloud auth application-default login"
    echo "   Or set GOOGLE_APPLICATION_CREDENTIALS environment variable"
    echo ""
    echo "🎯 Starting LangGraph Studio anyway (authentication may be needed for actual execution)..."
else
    echo "✅ Google Cloud authentication found"
fi

echo ""
echo "🎉 Starting LangGraph Studio..."
echo "📍 Studio will be available at: http://localhost:8123"
echo "📊 LangSmith tracing at: https://smith.langchain.com"
echo ""
echo "💡 Test with sample inputs from sample_inputs.json"
echo "🛑 Press Ctrl+C to stop the studio"
echo ""

# Start LangGraph Studio using uv with blocking allowed for now
# Use local venv explicitly to avoid path conflicts
unset VIRTUAL_ENV && uv run langgraph dev --allow-blocking

echo "👋 LangGraph Studio stopped"