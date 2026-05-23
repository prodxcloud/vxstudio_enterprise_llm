# changelogs.md — what shipped, when, and why

## 2026-04-25 — VxSupport v1.0 first fine-tune

- Trained `app/data/models/supportllm/` on Qwen2.5-0.5B-Instruct base, 1 epoch over 365 samples (`samples.csv`, `samples.json`, `generated.json`).
- Final mean train_loss **0.997** (started at 3.43). 78.5 s training + 10 s shard write on RTX 4050 Laptop (6 GB).
- Settings: `--per-device-train-batch-size 1 --gradient-accumulation-steps 8 --text-max-length 256 --no-eval`.
- Why `--no-eval`: with Qwen2's 151 936-vocab cross-entropy promoted to fp32 plus AdamW fp32 optimizer states, eval blew the 6 GB VRAM budget at step 10/21 (initial run) and step 20/41 (second). Training itself was healthy.
- Code change: added `no_eval` to `TrainConfig` in `app/services/ai/ml/train.py` and exposed `--no-eval` in `app/services/ai/ml/supportllm/train.py`. The flag flips `eval_strategy` to `"no"`.

## 2026-04-25 — README + welcome page rewrite for the 3 + 1 platform

- `README.md` rewritten around the 3 specialists + 1 reasoning core architecture; includes the full endpoint table for `app.py`, v1/v2/v3 routers, `/api/cloud`, `/v1/cloud`, `/v1/coding`, `/v1/support`, `/v1/ask`, `/monitoring/*`.
- `app/app.py`: FastAPI title bumped to "VxStudioEnterpriseLLM — ProdxCloud Multi-Model Platform (3 + 1)" v1.2.0; root `/` welcome page redesigned with model grid + quick-endpoint list; matrix-startup banner subtitle now lists VxThinking · VxCloud · VxCoder · VxSupport; system-info console box lists each specialist's prefix.

## 2026-04-24 — Multi-model monorepo reorg

- Datasets, models, and precompute folders now follow per-slug convention: `app/data/{datasets,models,precompute}/{thinkingllm,cloudllm,codingllm,supportllm}/`.
- Legacy paths (`data/vectorstore`, top-level `data/models/`) removed.
- Added `SpecialistBackend` shared base (`app/services/ai/ml/specialist_base.py`) so VxCloud, VxCoder, VxSupport share a single load+generate path. Per-model code only owns: model path, fallback HF id, system prompt, and route prefix.
- Each specialist gracefully falls back to its base HF model (Qwen2.5-0.5B-Instruct) when fine-tuned weights are absent, so every route is reachable from a clean checkout.

## 2026-04-24 — Universal `/v1/ask` dispatcher

- Single entry point that classifies prompts via keyword scoring (`app/services/ai/ml/universal.py`) and forwards to the right backend.
- Routing table publicly inspectable at `GET /v1/ask/routes`.
- `force_model` request field allows override (`thinkingllm | cloudllm | codingllm | supportllm`).

## 2026-04-22 — Local-host service action (Golang provisioner)

- `va_golang_infra_provisionner/services/dockerservices`: `CheckServiceReadiness` (`/api/v2/tenant/services/checking`) and `RunServiceAction` (`/api/v2/tenant/services/action`) now detect `localhost`/`127.0.0.1`/empty hostname and execute via `exec.Command("bash", "-c", ...)` instead of vault + SSH.
- Frontend unchanged — operator just types `localhost` in the Host/IP field and leaves SSH fields empty.
- Validation relaxed: SSH username + key pair only required for remote hosts.

## 2026-04-19 — Dockerfile + Jenkinsfile hardening

- `va_golang_infra_provisionner/Dockerfile` rewritten for multi-stage build, distroless runtime, non-root user, baked-in healthcheck against `/api/v2/health`.
- `Jenkinsfile`: pipeline now runs `go vet`, `golangci-lint`, and `gosec` before build; image tag = `${commit-short}-${build-number}`.

## 2026-04-13 — Provisioner v2 API freeze

- `/api/v2/*` route shape locked. Future additions go under `/api/v3/*`.
- API key middleware (`apiKey`) applied to every tenant-scoped route.
- 205 routes registered in `main.go`.

## 2026-04-09 — VxThinking core trained (legacy)

- Initial fine-tune of GPT-2 (distilgpt2 base, 6 layers / 768 hidden / 50 257 vocab) into `app/data/models/thinkingllm/`.
- Training data: deployment-style CSV with `prompt` + `intent` columns, formatted as instruction-tuning pairs by `row_to_text()` in `train.py`.
- Source dataset has since been moved out of the repo; the weights remain.

## 2026-04-06 — Vault federation

- `/api/v2/setup/cyberark-credentials` and `/api/v2/setup/external-vault-credentials` shipped.
- Customers can now keep secrets in their own CyberArk / HashiCorp Vault instance; ProdxCloud only stores a reference, not the secret value.

## 2026-03 — Multi-cloud parity

- Database provisioning extended to Azure SQL and Cloud SQL (parity with RDS).
- Kubernetes provisioning extended to AKS + GKE (parity with EKS).
- Storage provisioning extended to Azure Blob + GCS (parity with S3).

## 2026-02 — MetalDB launch

- Self-hosted Postgres/MySQL on bare metal or VMs (`/api/v2/tenant/provision/metaldb/*`). Multizone replication, automated backup/restore, query execution, database listing.
