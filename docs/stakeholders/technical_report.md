# Stakeholder Technical Report: KiranaAI System Architecture

## 1. System Components
The system is built on an asynchronous microservice architecture to easily handle concurrent WhatsApp message webhooks.
- **Frontend/Ingestion:** Evolution API (WhatsApp Webhook listener)
- **Backend Service:** FastAPI with async workers (`backend/app/api`, `backend/app/workers`)
- **Database:** Supabase (PostgreSQL) managed by SQLModel ORM
- **Intelligence Engine:** Local Ollama instance running custom SLMs (`backend/app/ml/inference`)

## 2. Telemetry and System Uptime
- **Logging:** All major actions (intent parsing, database writes) are logged directly to standard output and are aggregated via the Docker container logs.
- **Resilience:** The system utilizes a worker pattern to handle long-running LLM inferences without blocking the critical webhook ingestion layer.

## 3. Data Flow & Security
1. Webhooks from WhatsApp are signed and verified in FastAPI.
2. Only allowed admin phone numbers are processed by the system.
3. Intelligence extraction is done entirely strictly on-premises/local container. **No PII or pricing data leaks to public APIs.**

## 4. Current Capacity Limits
- **Throughput:** Based on average local hardware specs (e.g., Apple Silicon or consumer GPUs), the LLM layer can process roughly 4-6 intent queries per minute without queuing.
- **Scaling strategy:** Should volume increase beyond typical single-store loads, the Ollama container can be moved to dedicated cloud GPU hardware or scaled horizontally behind a load balancer.

## 5. Engineering Metrics
- Test coverage on critical Data Pipelines: Complete
- Target API response time: < 3 seconds per webhook round-trip.
- DB Operation latency: < 50ms.
