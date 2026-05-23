# vxstudio_enterprise_llm

**Enterprise Customer Service & Support SLM template — FAISS-backed, fine-tuned, sovereign.**

A drop-in Small Language Model stack for customer-service teams that need a private, citation-grounded support brain. Forked from the battle-tested vxthinkingllm specialist pattern, repositioned around customer-support workloads. Sold by prodxcloud as a starter kit — clients clone, drop in their own KB corpus, retrain, ship.

## What you get

- **4 specialist SLM slots** sharing one `SpecialistBackend` ([app/services/ai/ml/specialist_base.py](app/services/ai/ml/specialist_base.py)) — same load/generate contract across all of them so routing code stays symmetric.
- **FAISS retrieval per slug** — each model's corpus is embedded with `sentence-transformers/all-MiniLM-L6-v2`, persisted under `app/data/precompute/<slug>/`, and served via `/search` + `/query`.
- **In-process HuggingFace causal LM** — no vLLM, no OpenAI-compatible shim, no sidecar. The tokenizer + model live in the FastAPI process.
- **Auto-bootstrap** — `VXSTUDIO_ENTERPRISE_LLM_AUTO_PRECOMPUTE` and `VXSTUDIO_ENTERPRISE_LLM_AUTO_TRAIN` default to `true`, so first run builds the FAISS index and fine-tunes the model from the CSV/JSON corpus under `app/data/datasets/<slug>/`.

## Headline model: `supportllm` (Customer Service & Support)

The `supportllm` slug ([app/services/ai/ml/supportllm/](app/services/ai/ml/supportllm/)) is the customer-service flagship. Drop your KB articles, ticket history, runbooks, FAQ exports into `app/data/datasets/supportllm/` (CSV with `question,answer,category` columns or JSON), and the auto-train pipeline does the rest.

Endpoints:
- `GET  /v1/support/health` — readiness probe
- `GET  /v1/support/config` — corpus stats + model card
- `POST /v1/support/search` — vector similarity over the corpus
- `POST /v1/support/query` — retrieval-augmented Q&A with citations
- `POST /v1/support/generate` — direct LLM generation

The other slugs (`thinkingllm`, `codingllm`, `cloudllm`) ship as live demos of the multi-model pattern — keep them, repurpose them, or strip them out depending on what the client buys.

## Run it

```bash
# Quick start (auto-trains on first run)
python -m app.app

# Production
uvicorn app.app:app --host 0.0.0.0 --port 8001 --workers 4

# Docker
docker run -p 8001:8001 vxstudio_enterprise_llm:latest
```

FastAPI listens on **port 8001** (paired with [vxstudio_enterprise_agent](../vxstudio_enterprise_agent/) on 8002).

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `VXSTUDIO_ENTERPRISE_LLM_AUTO_PRECOMPUTE` | `true` | Auto-build FAISS index if missing |
| `VXSTUDIO_ENTERPRISE_LLM_AUTO_TRAIN` | `true` | Auto-train SLM if model weights are missing |
| `USE_CUDA` | `false` | GPU inference |
| `VXSTUDIO_ENTERPRISE_LLM_CACHE_EMBEDDINGS` | `true` | L1 query-embedding cache (TTL 1h) |
| `VXSTUDIO_ENTERPRISE_LLM_CACHE_SEARCH` | `true` | L2 search-result cache (TTL 30m) |

## Pairing

This repo is the **brain**. The [vxstudio_enterprise_agent](../vxstudio_enterprise_agent/) repo is the **orchestrator** — a LangChain ReAct agent (Customer Onboarding + Customer Training) that calls these endpoints as tools.

## Lineage

Forked from `SLM-Models/vxthinkingllm` (the prodxcloud internal multi-SLM platform). Identical code shape — only the brand identifiers, headline positioning, and default port (8001 vs 8745) differ.
