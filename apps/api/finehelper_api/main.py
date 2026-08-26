from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from urllib.parse import unquote

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from finehelper_api.deps import AuthDep
from finehelper_api.routers import auth, chat, datasets, jobs, ops, orgs, projects
from finehelper_core.db import init_db, make_engine, make_session_factory
from finehelper_core.jobs.loop import run_worker_loop
from finehelper_core.settings import get_settings
from finehelper_core.storage import LocalObjectStore, build_store


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    engine = make_engine(settings)
    await init_db(engine)
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = make_session_factory(engine)
    app.state.store = build_store(settings)
    stop = asyncio.Event()
    worker_task = None
    if settings.fh_embedded_worker:
        worker_task = asyncio.create_task(run_worker_loop(stop, "api-embedded"))
    yield
    stop.set()
    if worker_task:
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass
    await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Finehelper API",
        version="0.1.0",
        description="Control plane for dataset versioning, fine-tunes, evals, and deploys.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.web_origin, "http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(auth.router)
    app.include_router(orgs.router)
    app.include_router(projects.router)
    app.include_router(datasets.router)
    app.include_router(jobs.router)
    app.include_router(ops.router)
    app.include_router(chat.router)

    @app.get("/healthz")
    async def healthz():
        return {"ok": True, "service": "finehelper-api"}

    @app.put("/v1/internal/local-upload/{key:path}")
    async def local_upload(key: str, request: Request, auth: AuthDep):
        store = request.app.state.store
        if not isinstance(store, LocalObjectStore):
            raise HTTPException(400, "local upload is only enabled without R2")
        body = await request.body()
        decoded = unquote(key)
        if not decoded.startswith(str(auth.org_id)) and f"/{auth.org_id}/" not in f"/{decoded}/":
            # keys are uploads/{org}/{dataset}/filename
            parts = decoded.split("/")
            if str(auth.org_id) not in parts:
                raise HTTPException(403, "key is not in this org prefix")
        store.put(decoded, body, request.headers.get("content-type") or "application/octet-stream")
        return {"ok": True, "key": decoded, "bytes": len(body)}

    @app.get("/v1/internal/local-download/{key:path}")
    async def local_download(key: str, request: Request, auth: AuthDep):
        store = request.app.state.store
        decoded = unquote(key)
        if str(auth.org_id) not in decoded.split("/"):
            raise HTTPException(403, "key is not in this org prefix")
        try:
            data = store.get(decoded)
        except FileNotFoundError as exc:
            raise HTTPException(404, "not found") from exc
        return Response(content=data, media_type="application/octet-stream")

    return app


app = create_app()
