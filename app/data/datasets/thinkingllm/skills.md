# skills.md — VxThinking & ProdxCloud capability sheet

This is the canonical list of what the **ProdxCloud** stack (Golang provisioner `va_golang_infra_provisionner` + the 3+1 LLM platform) can do today. VxThinking uses this to know what it can promise an operator and what to dispatch where.

## vxcli — end-user CLI surface

VxThinking dispatches commands through this CLI when an operator wants to act. Recent additions:

- **`vxcli install list`** — discover the embedded service catalog (no network required).
- **`vxcli install <service> [--mode baremetal|docker|kubernetes]`** — single command for any of 53+ services. K8s mode bypasses SSH and runs locally against the operator's kubectl context.
- **`vxcli deploy <stack>`** — `react`, `nextjs`, `fastapi`, `static`, `nodejs`, `golang`, `cpp`, `python`, `django`, `php`, `rust` (11 stacks; up from 4 in the previous build).
- **`vxcli deploy container <name> --image <img> --port h:c`** — single Docker container deploy over SSH (no app build).
- **`vxcli deploy --service iam --resource-type policy --policy-document <file.json>`** — create an AWS IAM customer-managed policy from a local JSON document. (Bug-fixed Apr-2026: previously the server-side terraform template referenced an unset `local.policy_document`; now the CLI reads the file, validates JSON, and ships the body.)
- **`vxcli sessions {list,show,delete}`** — provisioning-session inspection.
- **`vxcli node {list,current,refresh,set-default}`** — tenant-node selection.
- **`vxcli init <name>`** — workspace scaffolding bound to the active tenant node.
- **`vxcli chat`** — multi-provider AI TUI (Anthropic / OpenAI / Google / OpenClaw).

## Multi-cloud provisioning (Golang provisioner — `/api/v2/tenant/provision/*`)

| Skill | Endpoint | Notes |
|---|---|---|
| Provision a multi-cloud VM | `POST /api/v2/tenant/provision/vm` | AWS · Azure · GCP · on-prem. Driven by `services/vm`. |
| Get VM status | `POST /api/v2/provision/vm/status` | Returns power state, public IP, tags. |
| VM action (start/stop/reboot) | `POST /api/v2/provision/vm/action` | |
| Provision Docker host | `POST /api/v2/tenant/provision/docker` | `services/dockerservices`. |
| Provision multi-cloud database | `POST /api/v2/tenant/provision/databases` | RDS · Azure SQL · Cloud SQL · MetalDB. |
| Provision MetalDB | `POST /api/v2/tenant/provision/metaldb` | Self-hosted Postgres/MySQL on bare metal or VMs. Also: `multizone`, `replicate`, `restore`, `backup`. |
| Provision Kubernetes cluster | `POST /api/v2/tenant/provision/kubernetescluster/deploy` | EKS · AKS · GKE · k3s. |
| Provision serverless | `POST /api/v2/tenant/provision/serverless` | Lambda · Azure Functions · Cloud Functions. |
| Provision CloudFront / CDN | `POST /api/v2/tenant/provision/cloudfront` | |
| Provision storage (S3/Blob/GCS) | `POST /api/v2/tenant/provision/storage` | + `/upload`, `/details`, `/objects`, `/object/download`, `/object/delete`, `/delete`. |
| Provision networks | `POST /api/v2/tenant/provision/networks` | VPC · subnets · NAT · IGW. |
| Provision security | `POST /api/v2/tenant/provision/security` | Security groups · NSGs · firewall rules. |
| Provision SSL | `POST /api/v2/tenant/provision/ssl` | ACM · Let's Encrypt · custom CA. |
| Provision GitHub Actions | `POST /api/v2/tenant/provision/githubactions` | CI/CD pipeline scaffolding. |
| Provision MCP server | `POST /api/v2/tenant/provision/mcp` | Model Context Protocol agent host. |
| Destroy provisioned resources | `POST /api/v2/tenant/provision/destroy` | Tags-based teardown. **Destructive — confirmation required.** |
| Tenant state management | `POST /api/v2/tenant/provision/state_management` | Terraform state migration / lock / unlock. |

## Application deployment to existing VMs (Golang — `/api/v1/infrastructure/services/*`)

Each language has matching `deploy` and `test-connection` endpoints:

- **Python**, **FastAPI**, **Django**, **Node.js**, **Next.js**, **React**, **Go**, **Rust**, **PHP**, **C++**, **Static website**.
- **VPN**: OpenVPN install · WireGuard install · client add/revoke · download config · status · action.
- **SSL**: install · test-connection.
- **cPanel / WHM**: install · test-connection.
- **OpenClaw**: install · configure · health · test-connection.
- **code-server / openvscode-server**: install (browser-based IDE).

## Embedded vxcli install catalog (53+ services × 3 variants)

Every script in `scripts/<service>/` is **bundled inside the `vxcli` binary** at build time (see `services/cli/cmd/install_catalog.go` — `//go:embed all:embedded_scripts`). End users install services with no repo access, by name:

```
vxcli install list                                                     → catalog browser
vxcli install <service>                          [baremetal default]   → SSH + native install
vxcli install <service> --mode docker            --host …              → SSH + 'docker run'
vxcli install <service> --mode kubernetes        (no --host needed)    → local kubectl/helm
```

When the user picks a service, `vxcli` extracts the embedded script to `/tmp`, **inlines `common/lib.sh` into it** so the SCP'd file is self-contained on a remote VM, then either:
- (`baremetal` / `docker`) SCPs to `/tmp/vxcli-install-<id>-…` and runs over SSH, or
- (`kubernetes`) executes locally against the user's current `~/.kube/config`.

### Services in the catalog (full triple = baremetal + docker + kubernetes)

```
anythingllm  certbot       directus     docuseal      elasticsearch  elk
flowiseai    forgejo       githubrunner gitlabrunner  grafana        headscale
hf-chat-ui   huly          jenkins      jfrog         keycloak       litellm
mailcow      mattermost    mongodb      mysql         n8n            ollama
opentelemetry openvpn       openwebui   portainer     postgres       powerdns
prometheus   rabbitmq      ragflow      redis         rocketchat     rustdesk
sonarqube    supabase      suricata    tailscale      vault          wireguard
```

### Services with subset coverage (baremetal-only or baremetal+docker)

```
docker  golang  java  kafka (no k8s)  kubernetes  nextcloud  nodejs
openclaw  php  python  temporal (no k8s)
```

### Special-case scripts

- **`mailcow --mode kubernetes`** installs **Mailu** (the Helm-supported FOSS mail stack) instead — mailcow upstream has no k8s support. Requires `--accept-alternative`.
- **`certbot --mode kubernetes`** installs **cert-manager** (`jetstack/cert-manager`) — the canonical k8s replacement. Requires `--email`.
- **`tailscale --mode kubernetes`** installs the official Tailscale operator via Helm. Requires `--oauth-client-id` / `--oauth-client-secret`.
- **`elasticsearch --mode kubernetes`** installs ECK (`elastic/eck-operator`) and applies a single-node `Elasticsearch` CR.
- **`supabase --mode kubernetes`** installs the community `supabase-community/supabase-kubernetes` chart.

### Adding new services

Drop `scripts/<service>/install_<service>.sh` (and optional `_docker_` / `_kubernetes_` variants) into the repo, then `bin/tenant_build_vxcli.sh`. The build script copies `scripts/` into `services/cli/cmd/embedded_scripts/`, the catalog rebuilds itself from `embed.FS` at runtime, and `vxcli install list` surfaces the new entry. **No CLI code changes required.**

## Server-side application deployment scripts (`scripts/deployments/`)

Invoked by Go provisioner handlers (`services/<stack>/<stack>.go`, `services/ai/agents/devopsagent.go`) when a user runs `vxcli deploy <stack>`. Every one of the **11 deploy stacks** has a dedicated script:

```
deploy_dockerized_fastapi.sh   deploy_fastapi_git.sh
deploy_dockerized_frontend.sh  deploy_frontend_git.sh
deploy_dockerized_nextjs.sh    deploy_dockerized_nodejs.sh
deploy_dockerized_django.sh    deploy_dockerized_python.sh
deploy_dockerized_php.sh       deploy_dockerized_golang.sh
deploy_dockerized_rust.sh      deploy_dockerized_cpp.sh
provision_containers.sh        (generic fallback)
```

Each auto-detects the framework from the source repo (e.g. Express vs Fastify in `nodejs`; Laravel vs raw PHP in `php`; CMakeLists vs Makefile in `cpp`), generates a Dockerfile + nginx config if absent, builds the image, ships it via SSH, and starts an nginx reverse proxy.

## Container orchestration (Docker on VMs)

- `POST /api/v2/tenant/container/{deploy,start,stop,remove}`
- `POST /api/v2/tenant/docker/container/{status,action}`
- `GET  /api/v2/tenant/docker/container/ws` (WebSocket stream)
- `POST /api/v2/tenant/services/checking` — service readiness scan (local or remote)
- `POST /api/v2/tenant/services/action` — quick actions (start/stop/restart) on a host
- `GET  /api/v2/tenant/services/inventory` — running services on a host
- `POST /api/v2/tenant/services/{chat,chat/stream,execute}` — interactive shell on the service via LLM gateway
- `GET  /api/v2/tenant/services/{llm-info, chat/history}` · `DELETE /chat/history`

## Kubernetes operations

- `GET  /api/v2/tenant/kubernetes/clusters` · `/cluster/{details,nodes,pods,services,deployments,ingresses,events,persistentvolumes,storageclasses}`
- `POST /api/v2/tenant/kubernetes/cluster/import` · `apply-manifest`
- `GET  /api/v2/tenant/kubernetes/exec` · `/node-shell` (WebSocket)

## Resource discovery & sync (cloud → ProdxCloud inventory)

- `POST /api/v2/tenant/resources/discover/{ec2,eks,iam,iam-policies,s3,security-groups,vpc}`
- `GET  /api/v2/tenant/resources/discover/:provider/:service`
- `POST /api/v2/tenant/resources/import` · `/import/batch`
- `POST /api/v2/tenant/resources/synchronize/:provider/:service` · `/synchronize/batch`

## Migrations

- `POST /api/v2/tenant/migrations/{plan,validate,execute}`
- `POST /api/v2/tenant/migrations/cancel/:session_id`
- `GET  /api/v2/tenant/migrations/status/:session_id`

## Backup & restore

- `POST /api/v2/tenant/backup/create` · `/restore`
- `GET  /api/v2/tenant/backup/list` · `/status/:job_id`
- `DELETE /api/v2/tenant/backup/:backup_id`

## Deployment agents (long-running auto-deploy workers)

- `POST /api/v2/tenant/deploy/agents` · `/validate`
- `GET  /api/v2/tenant/deploy/agents` · `/:deployment_id/{health,status,logs,history}`
- `PUT  /api/v2/tenant/deploy/agents/:deployment_id`
- `POST /api/v2/tenant/deploy/agents/:deployment_id/{rollback,scale}`
- `DELETE /api/v2/tenant/deploy/agents/:deployment_id`

## Billing & FinOps

- `POST /api/v2/tenant/billing/multicloud` — unified spend across AWS/Azure/GCP.
- `POST /api/v2/tenant/billing/optimization` — recommendations (rightsizing · reserved instances · spot · idle resources).

## Credentials vault (`workspace/`)

ProdxCloud stores **all** customer credentials (cloud, VM, Docker, DB, Git, OAuth, Okta, AI providers, messaging bots, payment, SMTP, SSL, kubeconfig) in a managed vault, with optional CyberArk / external Vault federation. Endpoints under `/api/v2/setup/*` and read paths under `/api/v2/vault/*`.

Supported AI provider credential slots (read at runtime by the LLM gateway): **OpenAI, Anthropic, Gemini, DeepSeek, Qwen, HuggingFace, Azure OpenAI, Llama, Mistral, Cohere, Perplexity, Groq, Hermes, OpenClaw, Ollama**. ProdxCloud is multi-provider; a customer can switch backends per workspace.

## Observability

VxSupport owns Jira-like tickets; the Golang provisioner emits structured logs (`logs/`) and metrics. The LLM platform exposes `/monitoring/*` (Prometheus + JSON metrics, performance counters, log inspection, observability/status).

## What we do *not* do (today)

- We do not run real-time inference on third-party-hosted LLMs by default. The vault stores credentials so a customer *can* bring their own (BYOK) but the default path is local.
- We do not have a self-service billing portal for end-users yet (Q3 roadmap — see `todos.md`).
- We do not auto-remediate incidents without operator confirmation. VxThinking proposes; the human approves.
