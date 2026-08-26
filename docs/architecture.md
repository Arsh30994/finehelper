# Finehelper architecture

Control plane (API, MongoDB, web, CLI) is separate from the data plane (object storage, CPU workers, Modal GPUs, optional local runner). Jobs are the unit of work. Dataset versions are immutable. Deployments require an eval report.

HTTP layout: **routes → controllers → services → Mongo models**. Session tokens are JWTs (`apps/api/finehelper_api/jwt.py`). Frontend calls live in `apps/web/src/api/index.js`.

## Surfaces

- **Web** (`apps/web`) — projects, uploads, runs, evals, playground, settings.
- **CLI** (`apps/cli`) — `fh` talks to the same REST API; `finehelper.yaml` is the recipe.
- **API** (`apps/api`) — FastAPI on `0.0.0.0:$PORT`. OpenAPI at `/openapi.json`.

## Domain

Org → Project → Dataset → DatasetVersion (content digest) → Job → Run → EvalReport → Deployment.

Job types: `ingest`, `prepare`, `train`, `eval`, `export`, `deploy`.

States: `queued` → `running` → `uploading` → `succeeded` | `failed` | `cancelled`.

## Dataset pipeline

Uploads land in R2 (or `.data/storage` locally) under `{org_id}/…`. Prepare converts OpenAI chat, ShareGPT, Alpaca, CSV, and JSONL into canonical chat JSONL, validates assistant-final turns, optionally dedupes, splits with a stable hash, and writes an error report instead of failing on the first bad row.

## Training backends

`TrainingBackend` protocol: `validate`, `submit`, `poll`, `cancel`, `collect`.

Implementations: OpenAI, dry_run, lora_modal (Modal `train_qlora`), lora_local (CLI heartbeat).

## Eval and deploy

Golden JSONL + metrics (`exact_match`, `contains`, `json_valid`, `llm_judge`). Quality gate on the report. Deploy job refuses unless the report passed or `override_gate` is set.

Inference gateway: `POST /v1/chat/completions` routes to the provider model or dry-run echo.

## Security

Tenant `org_id` on every document. Provider secrets AES-GCM with `MASTER_KEY`. Login/signup issue HS256 JWTs (`SECRET_KEY`). API keys `fh_live_…` hashed at rest. Logs scrub `sk-` / `hf_` / bearer tokens. Presigned object keys are org-prefixed.

## Deploy topology

Render: web service (API) + background worker + MongoDB (URI) + Key Value (`noeviction`). Vercel: Next.js. Modal: GPU functions. Cloudflare R2: datasets and artifacts.
