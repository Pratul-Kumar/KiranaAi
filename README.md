# ZnShop — Digital Store Manager (KiranaAi)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111.0-05998b.svg)](https://fastapi.tiangolo.com/)

**ZnShop** is an AI-powered WhatsApp backend specifically designed for Indian Kirana stores. It streamlines inventory management, digital ledger (khata), and reorder logic using local Small Language Models (SLMs) like Mistral via Ollama.

---

## 🚀 Quick Start

The easiest way to get the entire system up and running is using the built-in orchestrator:

```bash
# 1. Install dependencies
pip install -r backend/requirements.txt

# 2. Run the full system (FastAPI, Celery, Redis, Dashboard)
# On Windows (if venv is blocked):
.\run.ps1

# Otherwise:
python run_system.py
```

*Note: Ensure you have [Ollama](https://ollama.com/) running locally for AI features.*

---

## 🏗️ Repository Architecture

This project follows a production-grade ML engineering structure:

- **`backend/`**: Core services, FastAPI app (`app/`), and database schemas (`data/`).
- **`dashboard/`**: Streamlit-based Admin Dashboard for store and vendor management.
- **`configs/`**: Centralized configuration and logging setup.
- **`pipelines/`**: Data orchestration, ingestion, and scheduled jobs.
- **`scripts/`**: Utility scripts including `seed_data.py` for demo environments.
- **`tests/`**: Comprehensive test suite for API and logic verification.
- **`run_system.py`**: A master script to manage all project services.

---

## 🛠️ Tech Stack

- **Web Framework:** FastAPI (Uvicorn)
- **Database:** Supabase (PostgreSQL)
- **AI / SLM:** Mistral (via Ollama)
- **Task Queue:** Celery & Redis
- **Dashboard:** Streamlit
- **Containerization:** Docker & Docker Compose

---

## 📦 Detailed Setup

1. **Environment:** Copy `backend/.env.example` to `backend/.env` and fill in your credentials (Supabase, WhatsApp Meta API, etc.).
2. **Database:** Initialize your Supabase project and execute the SQL schema found in [`backend/data/schema.sql`](backend/data/schema.sql).
3. **Local LLM:** Ensure Ollama is running (`ollama serve`) and the Mistral model is pulled (`ollama pull mistral`).
4. **Redis:** The orchestrator will attempt to start Redis via Docker if not already running.

---

## 🔄 WhatsApp Reorder Workflow

The system supports an interactive loop between Store Owners and Distributors:
1. **Owner Request**: Sends a message (e.g., "10 packets of bread needed").
2. **AI Intent Parsing**: The SLM extracts the product and quantity.
3. **Interactive Buttons**: The distributor receives an approval notification with buttons (**Approve**, **Decline**, **Update Price**).
4. **Billing**: Upon approval, a Tax Invoice is automatically generated and shared.

---

## 🧪 Development & Testing

**Run Formatters & Linters:**
```bash
black .
isort .
flake8 .
```

**Execute Test Suite:**
```bash
pytest tests/
```

For more detailed developer notes, see [DEVELOPER_SETUP.md](DEVELOPER_SETUP.md).
