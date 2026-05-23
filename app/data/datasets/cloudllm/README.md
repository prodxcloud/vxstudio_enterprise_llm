# CloudLLM Dataset — VxCloud v1.0

**Specialty:** Terraform, Kubernetes, Ansible, Helm, Dockerfile, cloud incident
runbooks, cost optimization, IaC security review, cloud/DevOps/SRE.

**Model served at:** `/v1/cloud/*`
**Weights output dir:** `app/data/models/cloudllm/`
**System prompt:** flags security lines with `# SECURITY:`, always emits
resource limits in Kubernetes manifests, refuses non-DevOps questions.

---

## What's in this folder

| File | Purpose |
|---|---|
| `samples.json` | 6 realistic records (Terraform / K8s / Ansible / runbook / cost / Dockerfile) — JSON array, picked up automatically. |
| `samples.csv`  | 4 companion CSV rows (S3 bucket / HPA / Helm / runbook). |
| `README.md`    | This file. |

Add more files in any of these formats — they are all consumed by the trainer:
`.csv`, `.json` (array of objects), `.txt`, `.pdf`, `.sql`, `.xlsx`, `.xls`.

> Note: use `.json` (a JSON array), **not** `.jsonl` — the shared loader uses
> `json.load()` and only globs `*.json`.

---

## Preferred record schema

```json
{
  "task": "terraform|kubernetes|ansible|helm|dockerfile|runbook|cost",
  "prompt": "Write a Terraform module that creates an AWS VPC ...",
  "intent": "iac_terraform|k8s_manifest|ansible_playbook|incident_response|cost_optimization",
  "cloud_provider": "aws|azure|gcp|any",
  "region": "us-east-1",
  "output": "<ideal response, with `# SECURITY:` comments where relevant>"
}
```

CSV mirrors the same columns:
```
task,prompt,intent,cloud_provider,region,output
```

---

## Commands — copy/paste from the repo root (`va_llm_v1/`)

### 1) Train CloudLLM

```bash
# Default: trains on everything in app/data/datasets/cloudllm/
python -m app.services.ai.ml.cloudllm.train --num-train-epochs 1

# With a specific base model (DevOps-strong coder on 16GB GPU):
python -m app.services.ai.ml.cloudllm.train \
  --model-name-or-path Qwen/Qwen2.5-Coder-7B-Instruct \
  --num-train-epochs 2

# CPU-only smoke test:
python -m app.services.ai.ml.cloudllm.train \
  --model-name-or-path distilgpt2 \
  --num-train-epochs 1 \
  --per-device-train-batch-size 1
```

Weights are written to `app/data/models/cloudllm/` (`config.json`,
`tokenizer.json`, `pytorch_model.bin`).

### 2) Start the server

```bash
python -m app.app
# or:  uvicorn app.app:app --host 0.0.0.0 --port 8001
```

On boot you'll see:
```
✓ VxCloud v1.0 loaded (from app/data/models/cloudllm, device=...)
```
If no trained weights exist, the backend falls back to the base model and logs
`degraded` — the route still responds so you can smoke-test before training.

### 3) Smoke-test the routes

```bash
# Health — also shows the absolute resolved paths the backend is using
curl -s http://localhost:8001/v1/cloud/health | jq
# {
#   "status": "healthy",
#   "model_name": "VxCloud v1.0",
#   "paths": {
#     "model_path":     ".../app/data/models/cloudllm",
#     "dataset_dir":    ".../app/data/datasets/cloudllm",
#     "precompute_dir": "",
#     "prefix":         "/v1/cloud"
#   }
# }

# Direct generation
curl -s -X POST http://localhost:8001/v1/cloud/generate \
  -H 'Content-Type: application/json' \
  -d '{
    "prompt": "Write a Kubernetes Deployment for a FastAPI service with 3 replicas, resource limits, and a readiness probe.",
    "max_new_tokens": 500,
    "temperature": 0.3
  }' | jq

# Query (adds richer payload: raw text, loaded_from, duration)
curl -s -X POST http://localhost:8001/v1/cloud/query \
  -H 'Content-Type: application/json' \
  -d '{"prompt": "How do I rotate IAM access keys safely?"}' | jq
```

### 4) Route via the universal endpoint (auto-classified)

```bash
curl -s -X POST http://localhost:8001/v1/ask \
  -H 'Content-Type: application/json' \
  -d '{"prompt": "Terraform module for an AWS VPC with KMS-encrypted flow logs"}' | jq
# → "routed_to": "cloudllm"
```

### 5) Override the model-weights path at runtime

```bash
CLOUDLLM_MODEL_PATH=/models/prodxcloud-vxcloud-v1 \
CLOUDLLM_DEVICE=cuda \
python -m app.app
```

---

## Hard rules baked into the system prompt

1. Output valid, runnable code with inline comments.
2. Flag every security-relevant line with a `# SECURITY:` comment.
3. Always include `resources.limits` (CPU + memory) in Kubernetes manifests.
4. Prefer least-privilege IAM; never use wildcards in policies.
5. If a request isn't DevOps/cloud, say so and suggest the right model.
