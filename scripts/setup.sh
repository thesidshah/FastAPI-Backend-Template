#!/bin/bash
# FastAPI Production Starter - Quick Setup Script

set -e

echo "=========================================="
echo "FastAPI Production Starter - Setup"
echo "=========================================="
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.11"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "Error: Python $required_version or higher is required. Found: $python_version"
    exit 1
fi
echo "✓ Python $python_version found"
echo ""

# Create virtual environment
echo "Creating virtual environment..."
if [ -d ".venv" ]; then
    echo "Virtual environment already exists. Skipping..."
else
    python3 -m venv .venv
    echo "✓ Virtual environment created"
fi
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate
echo "✓ Virtual environment activated"
echo ""

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip -q
echo "✓ pip upgraded"
echo ""

# Install dependencies
echo "Installing dependencies..."
echo "This may take a few minutes..."
pip install -e ".[dev]" -q
echo "✓ Dependencies installed"
echo ""

# Copy environment file
echo "Setting up environment configuration..."
if [ -f ".env" ]; then
    echo "⚠️  .env file already exists. Skipping..."
else
    cp .env.example .env
    echo "✓ .env file created from .env.example"
    echo ""
    echo "⚠️  IMPORTANT: Please edit .env and update the following:"
    echo "   - SECURITY_JWT_SECRET (use: openssl rand -hex 32)"
    echo "   - APP_CORS_ALLOW_ORIGINS"
    echo "   - Other environment-specific settings"
fi
echo ""

# Generate JWT secret suggestion
echo "=========================================="
echo "Security Configuration"
echo "=========================================="
echo "Generate a secure JWT secret with:"
echo "  openssl rand -hex 32"
echo ""
echo "Example secret (DO NOT use this in production):"
openssl rand -hex 32
echo ""

# Run tests
echo "=========================================="
echo "Running tests..."
echo "=========================================="
pytest -v
echo ""

# Setup complete
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Edit .env file with your configuration"
echo "  2. Start the development server:"
echo "     uvicorn app.main:app --factory --reload"
echo "  3. Visit http://localhost:8000/docs"
echo ""
echo "For production deployment:"
echo "  docker-compose up -d"
echo ""
echo "Happy coding! 🚀"
