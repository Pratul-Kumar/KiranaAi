# ZnShop — Digital Store Manager

ZnShop is an AI-powered WhatsApp backend for Indian Kirana stores. It manages inventory, ledger (khata), and reorder logic using local SLMs (Mistral/Ollama).

## Repository Architecture

This repository follows a strict production-grade ML engineering structure:
- `configs/`: Centralized parameters and logging setup.
- `pipelines/`: Data orchestration, ingestion, and scheduled jobs.
- `src/`: Reusable FastAPI core, services, ML inference logic, and database schemas.
- `docs/`: Concise architectural and experimental records.

## Setup Instructions

1. **Environment:** Copy `backend/.env.example` to `.env` and fill valid API/DB credentials.
2. **Dependencies:** Ensure Python 3.10+ and run `pip install -r requirements.txt`.
3. **Database:** Initialize Supabase (PostgreSQL) and execute `src/db/schema.sql`.
4. **Local LLM:** Ensure Ollama is running (`ollama serve` and `ollama pull mistral`).

## Run Commands

**Start the Webhook Server:**
```bash
python -m src.main
```

**Run Formatters & Linters:**
```bash
black src pipelines configs
isort src pipelines configs
flake8 src pipelines configs
```

**Execute Test Suite:**
```bash
pytest tests/
```
