from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from urllib.parse import unquote

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from finehelper_api.deps import AuthDep
from finehelper_api.ml.trust.model import get_trust_model
from finehelper_api.routes import (
    agent_router,
    auth_router,
    chat_router,
    datasets_router,
    jobs_router,
    ops_router,
    orgs_router,
    projects_router,
    trust_router,
)
from finehelper_api.security import (
    MAX_UPLOAD_BYTES,
    SecurityHeadersMiddleware,
    assert_secure_settings,
    new_request_id,
    sanitize_storage_key,
)
from finehelper_core.db import connect_mongo, ensure_indexes
from finehelper_core.jobs.loop import run_worker_loop
from finehelper_core.settings import get_settings
from finehelper_core.storage import LocalObjectStore, build_store


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    assert_secure_settings(
        app_env=settings.app_env,
        secret_key=settings.secret_key,
        master_key=settings.master_key,
    )
    mongo = connect_mongo(settings)
    await mongo.ping()
    await ensure_indexes(mongo)
    app.state.settings = settings
    app.state.db = mongo
    app.state.store = build_store(settings)
    get_trust_model(settings.trust_model_path)
    stop = asyncio.Event()
    worker_task = None
    if settings.fh_embedded_worker:
        worker_task = asyncio.create_task(run_worker_loop(stop, "api-embedded", mongo))
    yield
    stop.set()
    if worker_task:
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass
    mongo.close()


def create_app() -> FastAPI:
    settings = get_settings()
    docs_url = "/docs" if settings.enable_docs and not settings.is_production else None
    redoc_url = "/redoc" if settings.enable_docs and not settings.is_production else None
    openapi_url = "/openapi.json" if settings.enable_docs and not settings.is_production else None

    app = FastAPI(
        title="TrustMesh / Finehelper API",
        version="0.1.0",
        description="Thin-file trust scoring and fine-tune control plane.",
        lifespan=lifespan,
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_cors_origins(),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Org-Id", "X-Request-Id"],
        expose_headers=["X-Request-Id"],
        max_age=600,
    )
    app.include_router(auth_router)
    app.include_router(orgs_router)
    app.include_router(projects_router)
    app.include_router(datasets_router)
    app.include_router(jobs_router)
    app.include_router(ops_router)
    app.include_router(chat_router)
    app.include_router(trust_router)
    app.include_router(agent_router)

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        rid = request.headers.get("x-request-id") or new_request_id()
        request.state.request_id = rid
        response = await call_next(request)
        response.headers["X-Request-Id"] = rid
        return response

    @app.exception_handler(Exception)
    async def unhandled_exception(request: Request, exc: Exception):
        # Never leak stack traces to clients in production
        if settings.is_production:
            return JSONResponse(
                status_code=500,
                content={"detail": "internal error", "request_id": getattr(request.state, "request_id", None)},
            )
        return JSONResponse(status_code=500, content={"detail": str(exc)})

    @app.get("/healthz")
    async def healthz(request: Request):
        await request.app.state.db.ping()
        return {"ok": True, "service": "finehelper-api", "db": "mongo"}

    @app.put("/v1/internal/local-upload/{key:path}")
    async def local_upload(key: str, request: Request, auth: AuthDep):
        store = request.app.state.store
        if not isinstance(store, LocalObjectStore):
            raise HTTPException(400, "local upload is only enabled without R2")
        body = await request.body()
        if len(body) > MAX_UPLOAD_BYTES:
            raise HTTPException(413, "upload too large")
        decoded = sanitize_storage_key(unquote(key), str(auth.org_id))
        store.put(decoded, body, request.headers.get("content-type") or "application/octet-stream")
        return {"ok": True, "key": decoded, "bytes": len(body)}

    @app.get("/v1/internal/local-download/{key:path}")
    async def local_download(key: str, request: Request, auth: AuthDep):
        store = request.app.state.store
        decoded = sanitize_storage_key(unquote(key), str(auth.org_id))
        try:
            data = store.get(decoded)
        except FileNotFoundError as exc:
            raise HTTPException(404, "not found") from exc
        return Response(
            content=data,
            media_type="application/octet-stream",
            headers={"Content-Disposition": "attachment"},
        )

    return app


app = create_app()
