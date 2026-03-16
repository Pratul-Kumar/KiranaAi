# 🏪 ZnShop — Digital Store Manager

> **AI-powered WhatsApp backend for Indian Kirana stores.**  
> Free. Self-hosted. Production-ready.

---

## Project Overview

ZnShop modernises traditional Kirana stores by using WhatsApp as the primary interface. Store owners interact via voice or text in Hinglish; the system routes AI-parsed intents to inventory, khata, and reorder workflows — all without any app installation.

---

## Architecture

```
User (WhatsApp)
        │
        ▼
Meta Graph API
        │
        ▼
FastAPI Backend  ──────►  Supabase (PostgreSQL)
   │       │
   │       └──► Celery Worker  ──►  Redis
   │
   └──►  Ollama (local SLM — Mistral)

Streamlit Admin Dashboard  ──────►  FastAPI /admin/* (JWT)
```

---

## Features

| Feature | Description |
|---|---|
| **🎙️ Voice-First Intent** | Hinglish SLM parsing via local Mistral (Ollama) |
| **📦 Interactive Reorder** | Approve / Decline / Update Price via WhatsApp buttons |
| **📜 Smart Tax Invoicing** | Auto-generated bills sent to both parties |
| **📈 Enhanced Demand Sensing** | Time-decayed scoring with seasonality signals |
| **📔 Digital Khata** | Customer ledger with automated lead-score calculation |
| **🛡️ GDPR Compliance** | Hard-delete endpoint with audit logging |
| **🔐 Admin Dashboard** | Streamlit UI with JWT auth for full store management |
| **🧑‍🤝‍🧑 Multi-Tenant** | Isolated stores, vendors, inventory, and khata per tenant |

---

## Tech Stack

| Layer | Technology |
|---|---|
| API | FastAPI 0.111 + Uvicorn |
| Database | Supabase (PostgreSQL + LTREE) |
| AI / SLM | Ollama (Mistral) |
| Task Queue | Celery 5.4 + Redis 7 |
| Security | JWT (python-jose) + bcrypt (passlib) |
| Rate Limiting | SlowAPI |
| Admin UI | Streamlit 1.35 |
| Infrastructure | Docker & Docker Compose |

---

## Installation

### 1. Prerequisites

- Docker & Docker Compose
- [Ollama](https://ollama.com/) running locally (`ollama pull mistral`)
- A [Supabase](https://supabase.com) project

### 2. Clone & Configure

```bash
git clone https://github.com/your-username/znshop.git
cd znshop
cp backend/.env.example backend/.env
# Fill in SUPABASE_URL, SUPABASE_KEY, SUPABASE_SERVICE_ROLE_KEY,
# WHATSAPP_*, ADMIN_PASSWORD, SECRET_KEY
```

### 3. Database Setup

1. Create a [Supabase](https://supabase.com) project.
2. Enable the `ltree` and `uuid-ossp` extensions (Database → Extensions).
3. Run [`backend/data/schema.sql`](backend/data/schema.sql) in the SQL Editor.
4. Seed demo data:

```bash
# From project root (requires Python + backend deps installed locally):
pip install -r backend/requirements.txt
python scripts/seed_data.py
```

---

## Docker Setup

```bash
docker-compose up --build
```

| Service | URL |
|---|---|
| API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Admin Dashboard | http://localhost:8501 |
| Redis | localhost:6379 |

---

## Admin Dashboard Usage

Open **http://localhost:8501** and log in with the credentials from your `.env` file
(`ADMIN_EMAIL` / `ADMIN_PASSWORD`).

**Sections:**

| Section | What You Can Do |
|---|---|
| 📊 Dashboard | Overview metrics (stores, vendors, alerts) |
| 🏬 Stores | Create store owners, view all stores |
| 🚚 Vendors | Create vendors, assign vendors to stores |
| 📦 Inventory | View real-time stock levels per store |
| 📔 Khata | View customer balances and lead scores |
| 🔔 Alerts | Latest demand signals above threshold |
| 📢 Broadcast | Send WhatsApp message to all or selected stores |

---

## API Documentation

Full interactive docs at **http://localhost:8000/docs**.

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/health` | — | Health check |
| GET | `/api/v1/whatsapp/webhook` | — | Meta webhook verification |
| POST | `/api/v1/whatsapp/webhook` | — | Incoming WhatsApp messages |
| GET | `/api/v1/alerts` | — | Latest demand alerts (public) |
| GET | `/api/v1/inventory/{store_id}` | — | Public inventory view |
| POST | `/api/v1/admin/login` | — | Get JWT token |
| POST | `/api/v1/admin/stores` | JWT | Create a store |
| GET | `/api/v1/admin/stores` | JWT | List all stores |
| POST | `/api/v1/admin/vendors` | JWT | Create a vendor |
| GET | `/api/v1/admin/vendors` | JWT | List all vendors |
| POST | `/api/v1/admin/assign-vendor` | JWT | Link vendor to store |
| GET | `/api/v1/admin/inventory/{store_id}` | JWT | View stock by store |
| GET | `/api/v1/admin/khata/{store_id}` | JWT | View khata by store |
| POST | `/api/v1/admin/khata/add` | JWT | Add khata record |
| GET | `/api/v1/admin/alerts` | JWT | Alerts (admin view) |
| POST | `/api/v1/admin/broadcast` | JWT | Broadcast WhatsApp message |
| POST | `/api/v1/inventory/update` | JWT | Manual stock update |
| DELETE | `/api/v1/customers/{id}` | — | GDPR hard-delete |

---

## Testing Instructions

The smoke test suite lives in `tests/test_api.py`. It runs **with all Supabase calls mocked**,
so no live database is required.

```bash
# Run from the backend/ directory
cd backend
pytest ../tests/test_api.py -v
```

Expected output (7 tests):

```
tests/test_api.py::test_health                    PASSED
tests/test_api.py::test_webhook_verify_correct_token  PASSED
tests/test_api.py::test_webhook_verify_wrong_token    PASSED
tests/test_api.py::test_admin_login_wrong_password    PASSED
tests/test_api.py::test_admin_stores_requires_auth    PASSED
tests/test_api.py::test_docs_available                PASSED
tests/test_api.py::test_public_alerts_returns_json    PASSED
tests/test_api.py::test_khata_add_requires_auth       PASSED
```

### After Seeding — End-to-End Test

```bash
# Seed demo data first
python scripts/seed_data.py

# Quick health check
curl http://localhost:8000/health

# Get JWT token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/admin/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@znshop.local","password":"changeme"}' | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# List stores
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/admin/stores

# Public alerts
curl http://localhost:8000/api/v1/alerts
```

---

## Deployment Guide

### Production Docker Deployment

1. **Set strong secrets** in `backend/.env`:
   ```bash
   # Generate a secure JWT secret
   openssl rand -hex 32
   ```
   Replace `SECRET_KEY` and `ADMIN_PASSWORD` with generated values.

2. **Point Ollama** at the correct host. On Linux, `host.docker.internal` resolves automatically
   via `extra_hosts`. On macOS/Windows Docker Desktop, it resolves natively.

3. **Run in detached mode**:
   ```bash
   docker-compose up -d --build
   ```

4. **View logs**:
   ```bash
   docker-compose logs -f backend
   # Log files also written to ./logs/app.log
   ```

5. **Scale workers** (optional):
   ```bash
   docker-compose up -d --scale worker=2
   ```

6. **Expose to internet** (for WhatsApp webhooks):
   - Point your domain / reverse proxy to port `8000`.
   - Register the webhook at: `https://yourdomain.com/api/v1/whatsapp/webhook`
   - Set `WHATSAPP_VERIFY_TOKEN` to the value in your Meta App Dashboard.

---

## Developer Setup

For the full local developer environment including ngrok webhook testing, see [DEVELOPER_SETUP.md](DEVELOPER_SETUP.md).

---

## Demo Data

After running `python scripts/seed_data.py`:

**Stores:** Ravi Kirana · Gupta General Store · Lakshmi Stores · Patel Mart  
**Vendors:** Milk Supplier · Maggi Distributor · Rice Supplier · Tea Supplier · Biscuit Distributor · Oil Supplier  
**SKUs per store:** Milk, Bread, Sugar, Maggi, Tea, Rice, Biscuits, Oil (stock: 50 each)  
**Customers per store:** Ramesh, Priya, Arjun

---

## License

MIT — see [LICENSE](LICENSE).
