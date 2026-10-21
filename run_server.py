#!/usr/bin/env python3
"""
FIFA 16 Revival Server - Main Entry Point
Starts the Blaze protocol server, FUT HTTP API, and UDP relay.
"""

import asyncio
import json
import logging
import os
import signal
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from server.blaze.redirector import BlazeRedirector
from server.blaze.auth_server import BlazeAuthServer
from server.fut_api.app import FUTApiServer
from server.database.db import Database
from server.logging_setup import setup_logging


def load_config():
    config_path = Path(__file__).parent / "config" / "server_config.json"
    with open(config_path, "r") as f:
        return json.load(f)


async def main():
    config = load_config()
    setup_logging(config["logging"])

    log = logging.getLogger("fifa16")
    log.info("=" * 60)
    log.info("  FIFA 16 Revival Server v%s", config["version"])
    log.info("=" * 60)

    db = Database(config["database"])
    await db.initialize()
    log.info("Database initialized: %s", config["database"]["path"])

    services = []

    redirector = BlazeRedirector(config["blaze"], db)
    services.append(redirector)

    auth_server = BlazeAuthServer(config["blaze"], db)
    services.append(auth_server)

    fut_api = FUTApiServer(config["fut_api"], db)
    services.append(fut_api)

    for service in services:
        try:
            await service.start()
            log.info("Started: %s", service.name)
        except Exception as e:
            log.error("Failed to start %s: %s", service.name, e)
            raise

    log.info("All services running. Press Ctrl+C to stop.")
    log.info("Blaze redirector: %s:%s",
             config["blaze"]["host"], config["blaze"]["redirector_port"])
    log.info("FUT API: %s:%s",
             config["fut_api"]["host"], config["fut_api"]["port"])

    stop_event = asyncio.Event()

    def signal_handler():
        log.info("Shutdown signal received")
        stop_event.set()

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, signal_handler)
        except NotImplementedError:
            pass

    try:
        await stop_event.wait()
    except KeyboardInterrupt:
        pass

    log.info("Shutting down...")
    for service in services:
        await service.stop()
        log.info("Stopped: %s", service.name)

    await db.close()
    log.info("Goodbye.")


if __name__ == "__main__":
    asyncio.run(main())
