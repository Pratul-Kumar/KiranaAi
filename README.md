# 🏪 Digital Store Manager (MVP)

> **Empowering Indian Kirana Stores with AI-Driven Voice Management & Demand Sensing.**

Digital Store Manager is a lean micro-SaaS designed to modernize traditional retail. By leveraging WhatsApp as the primary interface, it provides shopkeepers with a powerful AI assistant that handles stock updates, customer credit (Khata), and proactive reorder alerts—all via voice or text messages.

---

## ✨ Core Features

| Feature | Description |
| :--- | :--- |
| **🎙️ Voice-First Intent** | SLM-based parsing of Hinglish commands (*"5 packet doodh update karo"*) to automate stock updates. |
| **📈 Demand Sensing** | Predictive engine that monitors sales velocity and triggers proactive alerts for high-demand periods. |
| **📔 Digital Khata** | Automated customer ledger management with dynamic lead scoring for credit risk assessment. |
| **🔔 Proactive Nudges** | Automated WhatsApp reminders for payment collection and re-engagement of dormant customers. |
| **🛡️ Privacy First** | Built-in GDPR/Consent management with easy data deletion for compliance. |

---

## 🛠️ Tech Stack

- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (High-performance Python)
- **Database**: [Supabase](https://supabase.com/) (PostgreSQL with LTREE for hierarchy)
- **AI/LLM**: Local SLM (Mistral via [Ollama](https://ollama.com/)) + Bhashini ASR Abstraction
- **Task Queue**: [Celery](https://docs.celeryq.dev/) + [Redis](https://redis.io/)
- **Infrastructure**: Docker & Docker Compose

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.10+
- Docker & Docker Compose
- [Ollama](https://ollama.com/) (running locally)

### 2. Environment Setup
```bash
# Clone the repository
git clone https://github.com/your-username/digital-store-manager.git
cd digital-store-manager

# Configure environment
cp backend/.env.example backend/.env
# Update backend/.env with your Supabase and WhatsApp credentials
```

### 3. Database Initialization
1. Create a project on [Supabase](https://supabase.com).
2. Execute the DDL in [`backend/data/schema.sql`](backend/data/schema.sql) using the Supabase SQL Editor.
3. Ensure the `ltree` extension is enabled.

### 4. Launch with Docker
```bash
docker-compose up --build
```
The API will be available at `http://localhost:8000`.

---

## 🧪 Testing the Webhook
You can simulate a WhatsApp message using the provided test script:
```bash
python test_webhook.py
```

---

## 🏗️ Project Structure
```text
.
├── backend/
│   ├── app/
│   │   ├── api/          # Route handlers (WhatsApp, Compliance)
│   │   ├── services/     # AI, Inventory, Demand engines
│   │   ├── db/           # Supabase client & DB utils
│   │   └── worker/       # Celery background tasks
│   ├── data/             # SQL Schema & Migrations
│   └── main.py           # FastAPI Entrypoint
├── docker-compose.yml
└── test_webhook.py       # E2E Simulation Script
```

---

## 📄 License
This project is licensed under the MIT License - see the LICENSE file for details.
