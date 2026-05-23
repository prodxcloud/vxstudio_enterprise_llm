# CodingLLM Dataset — VxCoder v1.0

**Specialty:** code generation, multi-file edits, PR review, test writing,
vibe-coding across the ProdxCloud stack (FastAPI + React + TypeScript + K8s).

**Model served at:** `/v1/coding/*`
**Weights output dir:** `app/data/models/codingllm/`
**Precompute output:** `app/data/precompute/codingllm/index.json` (AST index).
**System prompt:** returns edits as XML search/replace diffs, writes tests
alongside features, never invents imports.

---

## What's in this folder

| File | Purpose |
|---|---|
| `samples.json` | 6 realistic records (FastAPI endpoint, React component, diff edit, PR review, pytest, refactor). |
| `samples.csv`  | 3 companion CSV rows (Python dict flatten, Go handler, vitest). |
| `README.md`    | This file. |

Add more files in any of these formats — all consumed by the trainer:
`.csv`, `.json` (array of objects), `.txt`, `.pdf`, `.sql`, `.xlsx`, `.xls`.

> Note: use `.json` (a JSON array), **not** `.jsonl` — the shared loader uses
> `json.load()` and only globs `*.json`.

---

## Preferred record schema

```json
{
  "task": "generate|edit|review|test|refactor",
  "language": "python|typescript|go|rust|...",
  "framework": "fastapi|react|nextjs|express|...",
  "prompt": "Write a FastAPI POST endpoint /users ...",
  "context": "<existing file content, function signature, or diff>",
  "output": "<ideal response: code, XML search/replace diff, or review notes>"
}
```

**Output format rules** (match the runtime system prompt):
- Edits to existing code → XML search/replace blocks:
  ```
  <<<<<<< SEARCH
  <old lines>
  =======
  <new lines>
  >>>>>>> REPLACE
  ```
- Whole-file generation → a single fenced code block with the correct language tag.

---

## Commands — copy/paste from the repo root (`va_llm_v1/`)

### 1) Precompute the AST index (do this before training)

```bash
# Index the whole repo into app/data/precompute/codingllm/index.json
python -m app.services.ai.ml.codingllm.precompute.index_codebase

# Index a different path (e.g. the user's repo):
python -m app.services.ai.ml.codingllm.precompute.index_codebase \
  --root /path/to/user-project \
  --out  app/data/precompute/codingllm/index.json
```

Works without `tree_sitter_languages` installed — Python files fall back to the
stdlib `ast` module. Install the full pack for TS/Go/Rust parsing:
```bash
pip install tree_sitter_languages
```

### 2) Train CodingLLM

```bash
# Default: trains on everything in app/data/datasets/codingllm/
python -m app.services.ai.ml.codingllm.train --num-train-epochs 1

# Recommended coder base (16GB+ GPU):
python -m app.services.ai.ml.codingllm.train \
  --model-name-or-path deepseek-ai/deepseek-coder-1.3b-instruct \
  --num-train-epochs 2 \
  --text-max-length 2048

# CPU-only smoke test:
python -m app.services.ai.ml.codingllm.train \
  --model-name-or-path distilgpt2 \
  --num-train-epochs 1 \
  --per-device-train-batch-size 1
```

Weights are written to `app/data/models/codingllm/`.

### 3) Start the server

```bash
python -m app.app
# or:  uvicorn app.app:app --host 0.0.0.0 --port 8001
```

### 4) Smoke-test the routes

```bash
# Health — also shows the absolute resolved paths the backend is using
curl -s http://localhost:8001/v1/coding/health | jq
# paths.model_path / dataset_dir / precompute_dir are printed and can be
# overridden via CODINGLLM_MODEL_PATH / CODINGLLM_DATASET_DIR / CODINGLLM_PRECOMPUTE_DIR.

# Generate — whole-file output
curl -s -X POST http://localhost:8001/v1/coding/generate \
  -H 'Content-Type: application/json' \
  -d '{
    "prompt": "Write a FastAPI endpoint /users that creates a user.",
    "language": "python",
    "framework": "fastapi",
    "max_new_tokens": 800,
    "temperature": 0.2
  }' | jq

# Edit — multi-file XML search/replace diff
curl -s -X POST http://localhost:8001/v1/coding/edit \
  -H 'Content-Type: application/json' \
  -d '{
    "instruction": "Add rate limiting (5/min per IP) to /users",
    "language": "python",
    "files": [
      {"path": "app/routers/users.py", "content": "@router.post(\"/users\")\nasync def create_user(payload: UserCreate):\n    ..."}
    ]
  }' | jq

# Review — diff review with focus areas
curl -s -X POST http://localhost:8001/v1/coding/review \
  -H 'Content-Type: application/json' \
  -d '{
    "diff": "- query = f\"SELECT * FROM users WHERE email = \"\"$EMAIL\"\"\n+ stmt = select(User).where(User.email == email)",
    "focus": "security,correctness"
  }' | jq
```

### 5) Route via the universal endpoint (auto-classified)

```bash
curl -s -X POST http://localhost:8001/v1/ask \
  -H 'Content-Type: application/json' \
  -d '{"prompt": "Refactor this function to use early returns."}' | jq
# → "routed_to": "codingllm"
```

### 6) Override the model-weights path at runtime

```bash
CODINGLLM_MODEL_PATH=/models/prodxcloud-vxcoder-v1 \
CODINGLLM_DEVICE=cuda \
python -m app.app
```

---

## Hard rules baked into the system prompt

1. Edits to existing code → XML search/replace diffs.
2. Whole-file generation → a single fenced code block.
3. Always write tests alongside features (pytest / vitest).
4. Never invent imports — referenced symbols must have visible imports.
5. Keep each function under 40 lines unless the task genuinely requires more.
