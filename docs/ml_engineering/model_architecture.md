# Model Architecture

## Overview
To provide a fast, cost-effective, and fully private solution for Indian Kirana stores, KiranaAI relies on a localized Small Language Model (SLM) architecture powered by Ollama.

## Core Models
1. **Primary Reasoning Engine:** `llama3` or `mistral` (via Ollama)
    - **Why local?** Zero API costs, complete data privacy for store owners, and robust performance on structured extraction tasks when provided with strict prompts.
2. **Demand Sensing Engine:** `demand_engine.py`
    - A heuristic/statistical model that calculates restock probability based on current stock levels versus historical minimums.

## Context Window & RAG Strategy
Because Kirana stores have highly variable inventory, the LLM cannot memorize it all. We use a lightweight dynamic context injection strategy:
1. **User Request:** "Do I have any Ashirvaad Atta?"
2. **Retrieval:** The backend queries the SQL database for items matching `*atta*`.
3. **Injection:** The retrieved database records are serialized into JSON and injected into the LLM's system prompt.
4. **Generation:** The LLM formulates a natural language response based on the injected facts.

## System Prompt Design
The prompt is heavily engineered to force JSON outputs.
```json
{
  "intent": "<INVENTORY|KHATA|INFO>",
  "entities": { ... }
}
```
**Constraints:**
- No conversational filler (no "Sure, I can help with that").
- Strict JSON structure.
- Fallback to safe responses if intent is unclear.

## Deployment Architecture
`Ollama` runs as a separate container alongside the FastAPI service. They communicate via HTTP on `localhost:11434`.
