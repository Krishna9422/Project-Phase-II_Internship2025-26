#!/bin/bash
# Analytics Dashboard Quick Start Guide

echo "🚀 Starting AI Code Reviewer with Interactive Analytics Dashboard..."
echo ""
echo "Prerequisites:"
echo "✓ Python 3.8+ installed"
echo "✓ Virtual environment activated (if using venv)"
echo ""

# Check if requirements are installed
echo "📦 Checking dependencies..."
python -m pip install -q -r requirements.txt

echo ""
echo "🧪 Running tests to generate metrics..."
echo "This will create pytest_results.json for the dashboard to use"
echo ""
python -m pytest --json-report --json-report-file=storage/reports/pytest_results.json -q

echo ""
echo "📊 Launching Analytics Dashboard..."
echo ""
echo "The app will open in your browser at http://localhost:8501"
echo ""
echo "⚡ Quick Tips:"
echo "  1. Navigate to 📊 Analytics Dashboard from the sidebar"
echo "  2. Upload Python or Java files to analyze"
echo "  3. View real-time metrics and visualizations"
echo "  4. Follow recommendations to improve code quality"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

streamlit run main_app.py
