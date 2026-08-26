from __future__ import annotations

import asyncio
import logging
import os
import signal

from finehelper_core.db import init_db, make_engine, make_session_factory
from finehelper_core.jobs.processor import JobProcessor
from finehelper_core.settings import get_settings
from finehelper_core.storage import build_store

log = logging.getLogger("finehelper.worker")


async def run_worker_loop(stop: asyncio.Event, worker_id: str | None = None) -> None:
    settings = get_settings()
    engine = make_engine(settings)
    await init_db(engine)
    sessions = make_session_factory(engine)
    store = build_store(settings)
    processor = JobProcessor(settings, store, sessions, worker_id or f"cpu-{os.getpid()}")
    log.info("cpu worker started id=%s", processor.worker_id)
    try:
        while not stop.is_set():
            did = await processor.tick()
            if not did:
                try:
                    await asyncio.wait_for(stop.wait(), timeout=1.5)
                except TimeoutError:
                    pass
    finally:
        await engine.dispose()


def install_sigterm(stop: asyncio.Event) -> None:
    loop = asyncio.get_event_loop()

    def _stop() -> None:
        log.info("SIGTERM received, finishing in-flight job then exiting")
        stop.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, _stop)
        except NotImplementedError:
            signal.signal(sig, lambda *_: stop.set())
