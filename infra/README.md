Render Blueprint lives at the repo root (`render.yaml`) so Render auto-detects it.

GPU workers: `modal deploy workers/gpu/modal_app.py`

Object storage: Cloudflare R2 via `S3_*` env vars (see `.env.example`).
