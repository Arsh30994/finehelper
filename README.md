# Finehelper

Workbench for the fine-tune loop: **ingest → version → train → eval → deploy**.

The web dashboard and the `fh` CLI share one control-plane API. Training backends are pluggable: OpenAI (and later Together/Google), Modal QLoRA, a local GPU runner, plus `dry_run` so you can exercise the whole loop without a GPU or provider key.

```
raw data → canonical dataset version → training job → eval report → deployment
```

## Layout

| Path | Role |
|---|---|
| `apps/web` | Next.js dashboard (Vercel) |
| `apps/api` | FastAPI control plane, binds `0.0.0.0:$PORT` (Render) |
| `apps/cli` | `fh` / `finehelper` CLI |
| `packages/core` | Domain models, storage, dataset pipeline, backends |
| `workers/cpu` | Render background worker (job claim loop) |
| `workers/gpu` | Modal QLoRA / GGUF / vLLM |
| `render.yaml` | API + worker + Postgres + Key Value |
| `finehelper.yaml.example` | Config-as-code recipe |

Architecture detail: [docs/architecture.md](docs/architecture.md).

## Local run

Python 3.12+ and Node 20+. From the repo root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e packages/core -e "packages/core[dev]" -e apps/api -e apps/cli
Copy-Item .env.example .env
python -m uvicorn finehelper_api.main:app --host 0.0.0.0 --port 8000 --reload
```

In another terminal:

```powershell
cd apps/web
npm install
npm run dev
```

Open http://localhost:3000 — sign up, create a project (backend `dry_run`), upload `examples/support.jsonl`, train, eval with `examples/golden.jsonl`, then chat in Playground.

CLI:

```powershell
fh auth signup
fh project support-bot --create --name "Support bot"
fh dataset upload .\examples\support.jsonl --name support-v1
fh train -f .\finehelper.yaml.example --dataset-version-id <id>
fh logs <job_id>
```

SQLite and local disk (`.data/`) are the default so you do not need Docker. Production uses Postgres + R2; see `.env.example`. Optional: `docker compose up -d` then set `DATABASE_URL` to Postgres.

Schema migrations live in `packages/core/alembic`. Render runs `alembic upgrade head` as the API pre-deploy command. Locally:

```powershell
alembic -c packages/core/alembic.ini upgrade head
```

## Production

- **API + CPU worker + Postgres + Redis:** `render.yaml` (API listens on `0.0.0.0:$PORT`, health `/healthz`, `FH_EMBEDDED_WORKER=0`).
- **Web:** deploy `apps/web` to Vercel with `NEXT_PUBLIC_API_URL` pointing at the Render API.
- **Object storage:** set `S3_*` to a Cloudflare R2 bucket. Render disks are ephemeral — never store datasets there.
- **GPUs:** `modal deploy workers/gpu/modal_app.py` then train with `backend: lora_modal`.
- Set `WEB_ORIGIN` and `API_PUBLIC_URL` on Render after first deploy.

## Training backends

- `dry_run` — synthetic metrics, no GPU, no provider (local demos).
- `openai` — Files + Fine-tuning API; store an org credential in Settings.
- `lora_modal` — QLoRA on Modal A100 (`train_qlora`).
- `lora_local` — CLI runner heartbeats; waiting for a GPU machine.
