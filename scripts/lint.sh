#!/bin/bash
# Code quality checks

set -e

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

echo "=========================================="
echo "Running code quality checks..."
echo "=========================================="
echo ""

# Black formatting
echo "1. Running Black (formatter)..."
black src tests
echo "✓ Black formatting complete"
echo ""

# Ruff linting
echo "2. Running Ruff (linter)..."
ruff check src tests --fix
echo "✓ Ruff linting complete"
echo ""

# MyPy type checking
echo "3. Running MyPy (type checker)..."
mypy src
echo "✓ MyPy type checking complete"
echo ""

echo "=========================================="
echo "All checks passed! ✨"
echo "=========================================="
