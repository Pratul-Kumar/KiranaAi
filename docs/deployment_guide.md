# ZnShop Public Deployment Guide

This guide deploys ZnShop for continuous public access (API + admin dashboard) on Render, Railway, or Fly.io.

## 1) Push code to GitHub

1. Create a GitHub repository.
2. Push this project root.
3. Ensure these files exist at root: `Dockerfile`, `docker-compose.yml`, `.env.example`, `Procfile`, `requirements.txt`.

## 2) Configure environment variables

Set these required variables on the hosting platform:

- `SUPABASE_URL=your_database_url` (MANDATORY)
- `SUPABASE_KEY=your_database_key` (MANDATORY)
- `ADMIN_EMAIL=admin@znshop.local`
- `ADMIN_PASSWORD=changeme` (or use `ADMIN_PASSWORD_HASH` and leave `ADMIN_PASSWORD` unused)
- `JWT_SECRET=secure_secret_key`
- `REDIS_URL=redis://<your-redis-host>:6379`
- `OLLAMA_URL=http://<ollama-host>:11434`

Recommended extras:

- `SUPABASE_SERVICE_ROLE_KEY=<service_role_key>`
- `PORT` (platform usually injects automatically)
- `CORS_ORIGINS=https://your-domain.com`
- `LOG_LEVEL=INFO`

## 3) Deploy on Render

Render offers different service types matching your project needs:

### 3.1) Key Value (Redis)
1. New → **Key Value**.
2. Name: `znshop-redis`.
3. After creation, copy the **Internal Redis URL** (e.g., `redis://red-xxxxxxxx:6379`). You'll need this for other services.

### 3.2) Web Service (Backend API)
1. New → **Web Service** → connect GitHub repo.
2. Name: `znshop-backend`.
3. Runtime: **Docker**.
4. Dockerfile Path: `backend/Dockerfile` (if prompt asks, otherwise it's detected).
5. Add Env Vars:
   - `PORT=8000`
   - `REDIS_URL` = (Internal Redis URL from step 3.1)
   - Include all variables from [Section 2](#2-configure-environment-variables).
6. Health Check Path: `/health`.

### 3.3) Web Service (Admin Dashboard)
1. New → **Web Service** → connect GitHub repo.
2. Name: `znshop-dashboard`.
3. Runtime: **Docker**.
4. Dockerfile Path: `backend/Dockerfile`.
5. Docker Command Override: `streamlit run /app/dashboard/admin_dashboard.py --server.port 8501 --server.address 0.0.0.0`
6. Add Env Vars:
   - `PORT=8501`
   - `ZNSHOP_API_URL` = `http://znshop-backend:8000/api/v1` (Internal URL)
   - Include all variables from [Section 2](#2-configure-environment-variables).

### 3.4) Background Worker (Celery)
1. New → **Background Worker** → connect GitHub repo.
2. Name: `znshop-worker`.
3. Runtime: **Docker**.
4. Docker Command Override: `celery -A app.workers.celery_app worker --loglevel=info`
5. Add Env Vars:
   - Match `znshop-backend` environment variables.

### 3.5) Background Worker (Celery Beat)
1. New → **Background Worker** → connect GitHub repo.
2. Name: `znshop-beat`.
3. Runtime: **Docker**.
4. Docker Command Override: `celery -A app.workers.celery_app beat --loglevel=info`
5. Add Env Vars:
   - Match `znshop-backend` environment variables.

## 4) Deploy on Railway

Railway uses a service-based architecture. You can deploy multiple services within a single project.

> [!IMPORTANT]
> **Workspace Requirement**: If you encounter the error `You must specify a workspaceId to create a project`, ensure you have created and selected a **Workspace** in your Railway dashboard before clicking "New Project". In the CLI, you may need to run `railway login` and then `railway link`.

### 4.1) Redis Database
1. New → **Database** → **Add Redis**.
2. Railway automatically adds `REDIS_URL` to your project's shared variables.

### 4.2) Backend Service (API)
1. New → **GitHub Repo** → connect your repo.
2. Settings → **Build** → **Dockerfile Path**: `backend/Dockerfile`.
3. Settings → **Deploy** → **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port ${PORT}`
4. Add Env Vars:
   - `PORT=8000`
   - All variables from [Section 2](#2-configure-environment-variables).
   - Ensure `REDIS_URL` is available (Railway handles this if Redis is in the same project).

### 4.3) Dashboard Service
1. New → **GitHub Repo** → (same repo).
2. Settings → **Build** → **Dockerfile Path**: `backend/Dockerfile`.
3. Settings → **Deploy** → **Start Command**: `streamlit run /app/dashboard/admin_dashboard.py --server.port 8501 --server.address 0.0.0.0`
4. Add Env Vars:
   - `PORT=8501`
   - `ZNSHOP_API_URL` = `http://znshop-backend.railway.internal:8000/api/v1` (Update with your backend service domain).
   - All variables from [Section 2](#2-configure-environment-variables).

### 4.4) Background Workers (Celery & Beat)
Repeat the steps for the backend repo, but change the **Start Command**:
- **Worker**: `celery -A app.workers.celery_app worker --loglevel=info`
- **Beat**: `celery -A app.workers.celery_app beat --loglevel=info`
- Ensure all environment variables match the backend service.

## 5) Deploy on Fly.io

1. `fly launch` in project root.
2. Configure secrets with `fly secrets set` for all required env vars.
3. Provision Redis (managed or external) and set `REDIS_URL`.
4. `fly deploy`.
5. Use `/health` for uptime checks.

## 6) Access the public admin dashboard

- Open: `https://your-domain.com/admin`
- Login required (`ADMIN_EMAIL` + password/hash).
- Supported actions:
  - Create/Delete store
  - Create/Delete vendor
  - Assign vendor to store
  - View inventory
  - View khata

## 7) Continuous runtime and restart behavior

- Set service restart policy (Render/Railway/Fly handle restart automatically).
- Keep auto-deploy from GitHub enabled for zero-touch updates.
- Use `/health` for platform liveness checks.

## 8) Seed demo testing data (6 stores, 8 vendors)

After deployment env vars are configured, run:

```bash
python scripts/seed_demo_data.py
```

This seeds:

- 6 stores
- 8 vendors
- sample inventory per store
