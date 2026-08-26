from __future__ import annotations

import asyncio
import logging
import os
import signal

from finehelper_core.db import connect_mongo, ensure_indexes
from finehelper_core.db.mongo import Mongo
from finehelper_core.jobs.processor import JobProcessor
from finehelper_core.settings import get_settings
from finehelper_core.storage import build_store

log = logging.getLogger("finehelper.worker")


async def run_worker_loop(stop: asyncio.Event, worker_id: str | None = None, mongo: Mongo | None = None) -> None:
    settings = get_settings()
    own_client = mongo is None
    if mongo is None:
        mongo = connect_mongo(settings)
        await ensure_indexes(mongo)
    store = build_store(settings)
    processor = JobProcessor(settings, store, mongo, worker_id or f"cpu-{os.getpid()}")
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
        if own_client:
            mongo.close()


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
