# SupportLLM Dataset — VxSupport v1.0

**Specialty:** IT support, internal docs Q&A, runbook lookup, Jira ticket
auto-answer, access / permission / install / configure how-tos.

**Model served at:** `/v1/support/*`
**Weights output dir:** `app/data/models/supportllm/`
**Precompute output:** `app/data/precompute/supportllm/index.json`
(and/or a Qdrant collection named `supportllm` when the server is reachable).
**System prompt:** always cites sources, structures answers as
`Diagnosis → Steps → Verify → Escalate`, refuses to guess when no source backs
the answer.

---

## What's in this folder

| File | Records | Purpose |
|---|---|---|
| `samples.json` | 22 | Foundation IT-support records (VPN, MFA, Slack, FileVault, …). |
| `samples.csv`  | 3 | CSV companions (password reset, runner disk, Docker Desktop). |
| `generated.json` | 340 | Generated prodxcloud.io / Studio / billing onboarding records. |
| `vxcli_auth_setup.json` | 8 | vxcli first-run, auth, node switching, doctor, configure. |
| `vxcli_deploy.json` | 7 | `vxcli deploy` for EC2, Next.js, EKS, Lambda, dry-run, troubleshooting. |
| `vxcli_marketplace_install.json` | 5 | Marketplace agents/solutions, embedded install catalog, custom scripts, container deploy. |
| `vxcli_agent_chat.json` | 5 | `vxcli agent` (git/devops/coding/parallel) and `vxcli chat` provider config. |
| `vxcli_cicd_sessions.json` | 5 | CI/CD pipelines, sessions, delete, import, pull. |
| `api_setup_credentials.json` | 5 | `/api/v2/setup/*` for AWS/AI/SSH/external Vault, deletion. |
| `api_provisioning.json` | 5 | `/api/v2/tenant/provision/*` for VM, S3, RDS, serverless, kubernetes apply-manifest. |
| `api_discovery_backup.json` | 5 | Resource discovery, batch sync, import, backup/restore, migrations, billing. |
| `api_workflow_metrics.json` | 5 | Workflow DAG engine, metrics/logs streaming, terminal/exec WebSockets, `/v1/ask` router, health probes. |
| `support_runbooks.json` | 5 | Provisioner 500s, Vault outage, invalid API key, unreachable app, orphan cleanup. |
| `workflow_endtoend.json` | 5 | Full e2e recipes (laptop→Next.js→AWS, EKS+app, GitHub→CI/CD, RDS+Lambda, fleet ops). |
| `README.md` | — | This file. |

Add more files in any of these formats — all consumed by the trainer:
`.csv`, `.json` (array of objects), `.txt`, `.pdf`, `.sql`, `.xlsx`, `.xls`.

> **Wiring**: `train.py` resolves `app/data/datasets/supportllm/` and globs every
> `*.json`, `*.csv`, … listed above — no code change needed when you drop a new
> file in. Same for `precompute/ingest_docs.py` which chunks every `*.json`
> alongside `*.md`/`*.txt`.
>
> **Filename caveat**: `train.py` has a `_skip_non_provisioning` filter that
> skips files whose names contain `observability`, `troubleshoot`, or
> `incident`. Avoid those tokens in new filenames (or update the filter in
> `train.py:625` if you want them included).

> Note: use `.json` (a JSON array), **not** `.jsonl` — the shared loader uses
> `json.load()` and only globs `*.json`.

---

## Preferred record schema

```json
{
  "task": "docs_qa|runbook|ticket_answer|troubleshoot",
  "prompt": "How do I request VPN access?",
  "category": "access|identity|tooling|compliance|infra|integrations",
  "sources": [
    {"title": "VPN Access Policy", "url": "https://confluence.acme/.../vpn"}
  ],
  "output": "Diagnosis: ...\n\nSteps:\n1. ...\n\nVerify: ...\n\nEscalate: ... Source: [title](url)."
}
```

CSV mirrors the same columns (`sources` is a JSON-encoded string inside the
CSV cell):
```
task,prompt,category,sources,output
```

---

## Commands — copy/paste from the repo root (`va_llm_v1/`)

### 1) Ingest docs into Qdrant (or local fallback)

```bash
# Ingest everything under supportllm/ using sentence-transformers/all-MiniLM-L6-v2.
# If Qdrant is reachable at $QDRANT_URL, the vectors go there; otherwise the
# script writes app/data/precompute/supportllm/index.json as a fallback.
python -m app.services.ai.ml.supportllm.precompute.ingest_docs \
  --source app/data/datasets/supportllm \
  --collection supportllm

# Ingest from a different source folder (e.g. a Confluence export):
python -m app.services.ai.ml.supportllm.precompute.ingest_docs \
  --source /path/to/confluence-export \
  --collection supportllm \
  --qdrant-url http://qdrant.internal:6333

# Override the embedding model:
python -m app.services.ai.ml.supportllm.precompute.ingest_docs \
  --embedding-model sentence-transformers/all-mpnet-base-v2
```

Requirements (install as needed):
```bash
pip install sentence-transformers qdrant-client
```

### 2) Train SupportLLM

```bash
# Default: trains on everything in app/data/datasets/supportllm/
python -m app.services.ai.ml.supportllm.train --num-train-epochs 1

# With an instruction-tuned base model (8-16GB GPU):
python -m app.services.ai.ml.supportllm.train \
  --model-name-or-path mistralai/Mistral-7B-Instruct-v0.2 \
  --num-train-epochs 2

# CPU-only smoke test:
python -m app.services.ai.ml.supportllm.train \
  --model-name-or-path distilgpt2 \
  --num-train-epochs 1 \
  --per-device-train-batch-size 1
```

Weights are written to `app/data/models/supportllm/`.

### 3) Start the server

```bash
python -m app.app
# or:  uvicorn app.app:app --host 0.0.0.0 --port 8001
```

### 4) Smoke-test the routes

```bash
# Health — also shows the absolute resolved paths the backend is using
curl -s http://localhost:8001/v1/support/health | jq
# paths.model_path / dataset_dir / precompute_dir are printed and can be
# overridden via SUPPORTLLM_MODEL_PATH / SUPPORTLLM_DATASET_DIR / SUPPORTLLM_PRECOMPUTE_DIR.

# Free-form support question
curl -s -X POST http://localhost:8001/v1/support/generate \
  -H 'Content-Type: application/json' \
  -d '{"prompt": "How do I request VPN access?"}' | jq

# Jira-style ticket answer
curl -s -X POST http://localhost:8001/v1/support/ticket \
  -H 'Content-Type: application/json' \
  -d '{
    "title": "Slack integration not posting to #deploys",
    "body": "Since Mondays migration, our deploy bot stopped posting. It used to work.",
    "reporter": "alice",
    "labels": ["slack", "ci"]
  }' | jq

# Incident runbook lookup
curl -s -X POST http://localhost:8001/v1/support/runbook \
  -H 'Content-Type: application/json' \
  -d '{
    "incident": "FileVault is disabled on my macOS laptop.",
    "service": "endpoint-compliance",
    "severity": "low"
  }' | jq
```

### 5) Route via the universal endpoint (auto-classified)

```bash
curl -s -X POST http://localhost:8001/v1/ask \
  -H 'Content-Type: application/json' \
  -d '{"prompt": "How do I reset my MFA device?"}' | jq
# → "routed_to": "supportllm"
```

### 6) Override the model-weights path at runtime

```bash
SUPPORTLLM_MODEL_PATH=/models/prodxcloud-vxsupport-v1 \
SUPPORTLLM_DEVICE=cuda \
python -m app.app
```

---

## Hard rules baked into the system prompt

1. Always cite sources when available — use the form `[title](url)`.
2. Structure every answer as `Diagnosis → Steps → Verify → Escalate`.
3. If no source supports the answer, say so and recommend escalating to
   `#it-help` rather than guessing.
4. Never expose secrets or internal tokens seen during training.
5. Use numbered steps for anything operational.
