# todos.md — ProdxCloud roadmap & open tickets

> **Format note for VxThinking**: each ticket has an `id`, `title`, `area`, `priority` (P0–P3), `status`, and a one-line description. When asked "what's next?" or "what's blocking the release?", I retrieve from this file.

## Now (in flight, this sprint)

- **PXC-401** · *VxThinking dataset bootstrap* · area: SLM-Models · P0 · **in-progress** — Author `soul.md`, `agent.md`, `skills.md`, `todos.md`, `changelogs.md` for `app/data/datasets/thinkingllm/` and re-run `precompute.py` so RAG has real grounding.
- **PXC-402** · *VxSupport first fine-tune* · area: SLM-Models · P0 · **done 2026-04-25** — 1 epoch on Qwen2.5-0.5B-Instruct, train_loss 3.43 → 0.99, weights at `app/data/models/supportllm/`.
- **PXC-403** · *VxCloud / VxCoder re-train* · area: SLM-Models · P1 · **pending** — Same recipe as PXC-402 (`--no-eval`, batch=1, seq=256) once specialist datasets are staged.
- **PXC-410** · *Local-host service action* · area: golang-provisioner · P1 · **done 2026-04-22** — `CheckServiceReadiness` and `RunServiceAction` now detect `localhost`/`127.0.0.1` and skip vault + SSH lookup, running `bash -c` directly. See `services/dockerservices`.
- **PXC-411** · *DevOps Agent connector* · area: golang-provisioner · P1 · **in-progress** — Wire `/api/v2/tenant/services/action` into the deployment agents pipeline so a chat command ("Deploy my frontend …") can trigger a real provision.

## Next (this quarter, ordered)

- **PXC-420** · *Multi-cluster K8s view* · area: golang-provisioner/kubernetes · P1 — Aggregate `/api/v2/tenant/kubernetes/clusters` across registered clusters into a single tenant pane.
- **PXC-421** · *MetalDB multizone GA* · area: golang-provisioner/databases · P1 — Promote `/api/v2/tenant/provision/metaldb/multizone` from beta to GA; add automated failover test.
- **PXC-430** · *VxThinking RAG over runbooks* · area: SLM-Models · P1 — Index `va_golang_infra_provisionner/scripts/**/*.sh` (network/dns_health_check.sh, network/network_latency_monitor.sh, network/open_port_scanner.sh, network/ssh_security_audit.sh, network/ssl_certificate_audit.sh, network/firewall_rule_check.sh, network/bandwidth_test.sh, cloud/aws/commands/provision_iam_role.sh, vm/fastapi_ssh_connect.sh) into FAISS so VxThinking can answer "which script handles X" without dispatching.
- **PXC-431** · *Universal dispatcher learning* · area: SLM-Models · P2 — Replace pure keyword routing in `universal.py` with keyword + cosine similarity to `skills.md` headings; keep keyword path as fallback when scores tie.
- **PXC-440** · *AWS resource discovery → cost view* · area: golang-provisioner/billings · P2 — Join `/api/v2/tenant/resources/discover/{ec2,eks,s3}` with `/api/v2/tenant/billing/multicloud` so an operator sees per-resource spend.
- **PXC-441** · *FinOps recommendations on idle* · area: golang-provisioner/billings · P2 — `/api/v2/tenant/billing/optimization` should flag instances < 5% CPU for 7 d.

## Soon (next quarter)

- **PXC-450** · *Self-service billing portal* · area: dashboard · P2 — End-user view of multi-cloud spend per workspace.
- **PXC-451** · *MCP server marketplace* · area: golang-provisioner/marketplace · P2 — Catalog of one-click MCP server installs.
- **PXC-460** · *Auto-remediation (opt-in)* · area: SLM-Models + golang-provisioner · P3 — VxThinking proposes a fix from a runbook; operator pre-approves a class of fixes (e.g. "restart pod on OOMKilled"); subsequent same-class incidents auto-fix.
- **PXC-470** · *Audit log to immutable store* · area: golang-provisioner/audit · P2 — Stream `services/audit` events to a write-once bucket / append-only log.

## Backlog

- **PXC-501** · Replace `distilgpt2` base for VxThinking core with a 1B Qwen2.5 once VRAM budget allows (currently 6 GB on dev laptop).
- **PXC-502** · Quantize specialist weights to 4-bit (bitsandbytes / GGUF) so all 3+1 fit on a single 8 GB card.
- **PXC-503** · Per-tenant FAISS shards (today: shared index per slug).
- **PXC-504** · WebSocket-based `/v1/ask/stream` for token-streaming responses.
- **PXC-505** · OpenAPI client SDKs (Python + Go) generated from the FastAPI schema.

## Blocked / waiting

- **PXC-601** · *vLLM evaluation* · waiting on infra — Need a 24 GB GPU to honestly compare vLLM throughput vs the current direct-HF path. Decision deferred to PXC-501 outcome.
- **PXC-602** · *Customer pilot #1 onboarding* · waiting on customer — VPC peering pending on their side.

## Won't do (deliberate non-goals)

- Hosted SaaS for ProdxCloud LLM gateway. The platform is **sovereign by design** — every install is on the customer's hardware. Closing the door on this keeps the security story clean.
- Calling external LLMs (OpenAI / Anthropic / Gemini) by default. The vault *stores* those credentials for BYOK customers but the default install does not phone home.
