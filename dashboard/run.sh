#!/bin/bash
# KSP Customer Intelligence Dashboard
# Run script for the unified dashboard

cd "$(dirname "$0")"

echo "🎯 Starting KSP Customer Intelligence Dashboard..."
echo ""

# Check if streamlit is installed
if ! command -v streamlit &> /dev/null; then
    echo "⚠️  Streamlit not found. Installing dependencies..."
    pip install -r requirements.txt
fi

# Run the unified dashboard
streamlit run unified_app.py --server.port 8501 --server.headless true

