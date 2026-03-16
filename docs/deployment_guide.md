# ZnShop Public Deployment Guide

This guide deploys ZnShop for continuous public access (API + admin dashboard) on Render, Railway, or Fly.io.

## 1) Push code to GitHub

1. Create a GitHub repository.
2. Push this project root.
3. Ensure these files exist at root: `Dockerfile`, `docker-compose.yml`, `.env.example`, `Procfile`, `requirements.txt`.

## 2) Configure environment variables

Set these required variables on the hosting platform:

- `ADMIN_EMAIL=admin@znshop.local`
- `ADMIN_PASSWORD=changeme` (or use `ADMIN_PASSWORD_HASH` and leave `ADMIN_PASSWORD` unused)
- `SUPABASE_URL=your_database_url`
- `SUPABASE_KEY=your_database_key`
- `JWT_SECRET=secure_secret_key`
- `REDIS_URL=redis://<your-redis-host>:6379`
- `OLLAMA_URL=http://<ollama-host>:11434`

Recommended extras:

- `SUPABASE_SERVICE_ROLE_KEY=<service_role_key>`
- `PORT` (platform usually injects automatically)
- `CORS_ORIGINS=https://your-domain.com`
- `LOG_LEVEL=INFO`

## 3) Deploy on Render

1. New **Web Service** → connect GitHub repo.
2. Environment: Docker.
3. Auto deploy: **Enabled**.
4. Health check path: `/health`.
5. Add env vars from step 2.
6. Deploy.

Example URLs:

- `https://znshop-api.onrender.com/admin`
- `https://znshop-api.onrender.com/docs`

## 4) Deploy on Railway

1. New Project → Deploy from GitHub.
2. Railway detects Dockerfile / Procfile.
3. Add env vars from step 2.
4. Add Redis service and set `REDIS_URL`.
5. Enable auto-deploy from main branch.

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
