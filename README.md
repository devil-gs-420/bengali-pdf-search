# 🇧🇩 বাংলা PDF সার্চ সিস্টেম
### Bengali PDF Folder Search System

A production-ready full-stack system to upload entire folders of Bengali voter-list PDFs, extract structured data with OCR, and search instantly across hundreds of thousands of records.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 📁 **Folder Upload** | Drag-and-drop multiple PDFs, real-time progress tracking |
| 🔍 **Instant Search** | Debounced multi-field search with Bengali Unicode support |
| 🤖 **Auto OCR** | Tesseract + EasyOCR fallback for scanned PDFs |
| 📊 **Dashboard** | Stats, top districts, recent activity |
| 📤 **Export** | CSV (UTF-8 BOM), Excel, JSON |
| 🔐 **Auth** | JWT with role-based access (admin/operator/viewer) |
| 🐳 **Docker** | One-command deployment |

---

## 🚀 Quick Start

### Option 1: Docker (Recommended)

```bash
git clone https://github.com/yourname/bengali-pdf-search
cd bengali-pdf-search

# Copy and configure environment
cp backend/.env.example backend/.env
# Edit backend/.env with your settings

docker-compose up -d
```

Open http://localhost — register the first account (auto-assigned admin role).

### Option 2: Manual Setup

```bash
bash scripts/setup.sh
```

**Start backend:**
```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload --port 8000
```

**Start frontend:**
```bash
cd frontend
npm run dev
```

---

## 🏗️ Architecture

```
bengali-pdf-search/
├── backend/                  # FastAPI Python backend
│   ├── app/
│   │   ├── api/             # Route handlers
│   │   ├── core/            # Config, security, logging
│   │   ├── db/              # SQLAlchemy models + database
│   │   ├── schemas/         # Pydantic schemas
│   │   └── services/        # PDF processing, search, export
│   ├── tests/               # pytest test suite
│   └── main.py              # FastAPI app entry
├── frontend/                 # React + TypeScript + Vite
│   └── src/
│       ├── pages/           # Dashboard, Search, Upload, Documents
│       ├── components/      # Layout, shared UI
│       ├── store/           # Zustand state
│       └── utils/           # Axios API client
├── docker/                  # Dockerfiles
├── nginx/                   # Reverse proxy config
└── docker-compose.yml
```

---

## 🔍 Search Fields

Search by any of these voter fields:

- **ভোটার নম্বর** (Voter ID)
- **নাম** (Name)
- **পিতার নাম** (Father's Name)
- **মাতার নাম** (Mother's Name)
- **জন্মতারিখ** (Birth Date)
- **জেলা** (District)
- **উপজেলা** (Upazila)
- **ইউনিয়ন** (Union)
- **ওয়ার্ড** (Ward)
- **গ্রাম** (Village)
- **পেশা** (Occupation)

---

## 🔌 API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | Login → JWT tokens |
| POST | `/api/upload` | Upload PDFs (multipart) |
| GET | `/api/upload/{id}/progress` | Poll processing progress |
| GET | `/api/search?q=...` | Multi-field search |
| POST | `/api/search` | Advanced search (POST body) |
| GET | `/api/documents` | List documents |
| POST | `/api/export` | Export CSV/Excel/JSON |
| GET | `/api/stats` | Dashboard statistics |
| GET | `/api/docs` | Swagger UI |

---

## 🐳 Docker Configuration

```yaml
# docker-compose.yml includes:
# - PostgreSQL 16
# - Redis 7
# - FastAPI backend (4 workers)
# - React frontend
# - Nginx reverse proxy
```

**Environment variables:**
```env
DB_USER=postgres
DB_PASSWORD=yourpassword
JWT_SECRET_KEY=your-jwt-secret
SECRET_KEY=your-app-secret
```

---

## 🔧 OCR Setup

**Tesseract (required for scanned PDFs):**
```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr tesseract-ocr-ben

# macOS
brew install tesseract
brew install tesseract-lang

# Verify Bengali support
tesseract --list-langs | grep ben
```

**EasyOCR** (auto-installed, used as fallback when Tesseract confidence < 60%)

---

## 🗃️ Database

Supports **SQLite** (development, zero config) and **PostgreSQL** (production).

```env
# SQLite (default)
DATABASE_URL=sqlite+aiosqlite:///./bengali_pdf_search.db

# PostgreSQL
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/dbname
```

---

## 🧪 Running Tests

```bash
cd backend
source venv/bin/activate
pytest tests/ -v --cov=app
```

---

## 📈 Performance Notes

- Async FastAPI with 4 Uvicorn workers
- ThreadPoolExecutor for CPU-bound PDF processing
- SHA-256 duplicate detection prevents reprocessing
- SQLAlchemy connection pooling
- Debounced frontend search (350ms)
- Paginated results (configurable page size)

---

## 🔒 Security

- Bcrypt password hashing (12 rounds)
- JWT access tokens (24h) + refresh tokens (30d)
- Rate limiting via Nginx
- File type validation (PDF only)
- SQL injection protection via SQLAlchemy ORM
- Security headers on all responses

---

## 📄 License

MIT License — see LICENSE file.
