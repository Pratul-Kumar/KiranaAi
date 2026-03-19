# Evaluation Results

## Key Metrics Benchmarks (v1.0)

| Metric | Target | Current Performance | Status |
|---|---|---|---|
| **Intent Classification Accuracy** | > 95% | 96.5% | PASS |
| **Entity Extraction Accuracy (Hinglish)** | > 90% | ~92% | PASS |
| **P90 Latency (Inference)** | < 3000ms | 2850ms | PASS |
| **API Webhook Response Time** | < 5000ms | 3100ms | PASS |
| **Hallucination Rate** | < 1% | ~0.5% | PASS |

## Methodology
Evaluation is performed automatically via the verification script `python backend/app/scripts/verify_system.py`.

### 1. Intent Classification
Evaluated on a static dataset of 200 common Kirana store phrases (e.g., "bhai khata likh", "stock mei dahi hai kya").

### 2. Entity Extraction
Evaluated by matching LLM JSON outputs against a golden dataset of expected Pydantic schema instantiations.

### 3. Latency
Measured across 500 API calls simulating peak load.
