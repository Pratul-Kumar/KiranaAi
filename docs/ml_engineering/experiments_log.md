# Experiment Logs

## Tracking Methodology
Starting with version 2.0 of the ML pipeline, we track all prompt engineering and hyperparameter tuning experiments using MLflow.
**Location:** `backend/app/ml/experiments/`

## Pre-MLflow Historical Experiments

### Experiment 001: Model Selection for Entity Extraction
**Goal:** Determine the best local model for extracting structured JSON (Item, Quantity, Price) from Hinglish text.
- **Candidates:** `Llama 3 (8B)`, `Mistral (7B)`
- **Prompt:** Few-shot JSON extraction.
- **Result:** Mistral (7B) was slightly faster on older hardware, but Llama 3 (8B) had a 15% higher accuracy rate on mixed Hindi-English ("5 packet maggi de do"). 
- **Winner:** Llama 3 (8B)

### Experiment 002: Latency Optimization
**Goal:** Reduce response time for WhatsApp messages.
- **Changes:** Lowered context window size, removed unnecessary chat history injection.
- **Result:** Latency dropped from ~4.5s to ~2.2s.

## Future MLflow Tracking
When running new tuning scripts, ensure the MLflow tracking URI is set.
```bash
export MLFLOW_TRACKING_URI=sqlite:///mlflow.db
python backend/app/ml/experiments/run_tuning.py
```
Recorded metrics will include:
- `accuracy`
- `latency_ms`
- `token_generation_rate`
