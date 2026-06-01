#!/usr/bin/env bash
# ─── Bengali PDF Search System - Local Setup Script ──────────────────────────
# Usage: bash scripts/setup.sh

set -e
echo "🇧🇩 Setting up Bengali PDF Search System..."

# ── System checks ─────────────────────────────────────────────────────────────
command -v python3 >/dev/null 2>&1 || { echo "Python 3.12+ required"; exit 1; }
command -v node >/dev/null 2>&1 || { echo "Node.js 18+ required"; exit 1; }

# ── Backend ───────────────────────────────────────────────────────────────────
echo ""
echo "📦 Setting up Python backend..."
cd backend

# Create virtual environment if not exists
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✓ Virtual environment created"
fi

source venv/bin/activate

# Install dependencies
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo "✓ Python dependencies installed"

# Copy env file
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "✓ Created .env from template (review and update values)"
fi

# Create directories
mkdir -p uploads exports logs
echo "✓ Directories created"

cd ..

# ── Frontend ──────────────────────────────────────────────────────────────────
echo ""
echo "📦 Setting up React frontend..."
cd frontend
npm install --legacy-peer-deps -q
echo "✓ Node.js dependencies installed"
cd ..

# ── OCR Check ─────────────────────────────────────────────────────────────────
echo ""
echo "🔍 Checking OCR installation..."
if command -v tesseract >/dev/null 2>&1; then
    echo "✓ Tesseract found: $(tesseract --version | head -1)"
    if tesseract --list-langs 2>&1 | grep -q "ben"; then
        echo "✓ Bengali language pack installed"
    else
        echo "⚠️  Bengali language pack missing"
        echo "   Ubuntu/Debian: sudo apt-get install tesseract-ocr-ben"
        echo "   macOS: brew install tesseract-lang"
    fi
else
    echo "⚠️  Tesseract not found"
    echo "   Ubuntu/Debian: sudo apt-get install tesseract-ocr tesseract-ocr-ben"
    echo "   macOS: brew install tesseract"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "To start development servers:"
echo "  Backend:  cd backend && source venv/bin/activate && uvicorn main:app --reload"
echo "  Frontend: cd frontend && npm run dev"
echo ""
echo "Or use Docker:"
echo "  docker-compose up"
