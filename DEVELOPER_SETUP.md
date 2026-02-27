# 🛠️ Developer Setup Guide

Follow these steps to set up the **Digital Store Manager** development environment.

## 1. Prerequisites
- **Python 3.10+**
- **Docker** (for Redis & Docker-compose)
- **Ollama** (for local SLM inference)
- **ngrok** (for local webhook testing)

## 2. Configuration (`.env`)
Create a `.env` file in the `backend/` directory based on `.env.example`.

| Variable | Description |
| :--- | :--- |
| `SUPABASE_URL` | Your project URL from the Supabase dashboard. |
| `SUPABASE_KEY` | Your project's Anon Key. |
| `SUPABASE_SERVICE_ROLE_KEY` | (Optional) Service role key for admin tasks. |
| `AI_MODEL_ENDPOINT` | Local Ollama endpoint (e.g., `http://localhost:11434/api/generate`). |
| `WHATSAPP_ACCESS_TOKEN` | Meta Graph API Access Token. |
| `WHATSAPP_VERIFY_TOKEN` | Custom string for webhook verification. |

## 3. Database Setup
1. Create a new project on [Supabase](https://supabase.com).
2. Execute the SQL schema found in [`backend/data/schema.sql`](backend/data/schema.sql).
3. Ensure the `ltree` extension is enabled in your project settings.

## 4. Run the Application

### Option A: Local Development
```bash
# 1. Install dependencies
pip install -r backend/requirements.txt

# 2. Start the FastAPI server
cd backend
uvicorn app.main:app --reload --port 8000

# 3. Start the Celery worker (in a new terminal)
celery -A app.worker.celery_worker worker --loglevel=info
```

### Option B: Docker Compose
```bash
docker-compose up --build
```

## 5. WhatsApp Reorder Workflow
The system supports an interactive loop between Store Owners and Distributors:
1. **Owner Request**: Sends a message like "10 Bread req".
2. **Distributor Notification**: Receives interactive buttons (**Approve**, **Decline**, **Update Price**).
3. **Price Memory**: The system remembers the last agreed price for future orders.
4. **Billing**: Once approved, the distributor generates a Tax Invoice which is automatically shared with the Owner.

## 6. Database Migrations
1. Execute the full SQL schema found in [`backend/data/schema.sql`](backend/data/schema.sql).
2. This single file now contains all core tables plus the new **Reorder & Billing** tracking system.

## 7. Testing the Webhook
To test the webhook locally:
1. Start an ngrok tunnel: `ngrok http 8000`.
2. Configure your Meta App webhook with the ngrok URL: `https://<ngrok-id>.ngrok-free.app/api/v1/whatsapp/webhook`.
3. Use the `test_webhook.py` script to simulate incoming events locally.

## 🛡️ Compliance & Safety
- All customer PII must be handled via the designated service layer.
- GDPR `delete_customer` calls trigger a hard delete across all linked tables.
