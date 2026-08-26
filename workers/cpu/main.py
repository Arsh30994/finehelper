"""Render CPU worker: claim jobs from MongoDB and run the data plane."""

from __future__ import annotations

import asyncio
import logging

from finehelper_core.jobs.loop import install_sigterm, run_worker_loop

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def main() -> None:
    stop = asyncio.Event()

    async def _run() -> None:
        install_sigterm(stop)
        await run_worker_loop(stop, "cpu-render")

    asyncio.run(_run())


if __name__ == "__main__":
    main()
