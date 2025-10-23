#!/bin/bash
# Test runner script with coverage

set -e

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

echo "=========================================="
echo "Running test suite..."
echo "=========================================="
echo ""

# Run tests with coverage
pytest \
    --cov=app \
    --cov-report=html \
    --cov-report=term-missing \
    --cov-report=xml \
    -v \
    "$@"

echo ""
echo "=========================================="
echo "Coverage report generated"
echo "=========================================="
echo "View HTML report: open htmlcov/index.html"
echo ""
