"""
Blaze Redirector Server

The first server the FIFA 16 client connects to. It redirects the client
to the main authentication server. Port 42127 is the standard Blaze
redirector port.
"""

import asyncio
import logging
import json
import time
from pathlib import Path

log = logging.getLogger("blaze.redirector")


class BlazeRedirector:
    """Blaze redirector - tells clients where to find the auth server."""

    def __init__(self, config, db):
        self.name = "Blaze Redirector"
        self.config = config
        self.db = db
        self.server = None
        self.host = config["host"]
        self.port = config["redirector_port"]

    async def start(self):
        self.server = await asyncio.start_server(
            self._handle_client,
            self.host,
            self.port
        )
        log.info("Redirector listening on %s:%s", self.host, self.port)

    async def stop(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()

    async def _handle_client(self, reader, writer):
        peer = writer.get_extra_info("peername")
        log.info("Redirector: new connection from %s:%s", peer[0], peer[1])

        try:
            data = await asyncio.wait_for(reader.read(4096), timeout=10.0)

            if not data:
                log.warning("Redirector: empty connection from %s", peer)
                writer.close()
                return

            self._journal_connection(peer, data)

            redirect_host = self.config.get("auth_host", self.host)
            redirect_port = self.config.get("ssl_port", 42133)

            response = self._build_redirect_response(redirect_host, redirect_port)

            writer.write(response)
            await writer.drain()

            log.info("Redirector: redirected %s to %s:%s",
                     peer, redirect_host, redirect_port)

        except asyncio.TimeoutError:
            log.warning("Redirector: timeout from %s", peer)
        except Exception as e:
            log.error("Redirector: error handling %s: %s", peer, e)
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    def _build_redirect_response(self, host: str, port: int) -> bytes:
        """Build a Blaze redirect response packet."""
        from server.blaze import BlazePacket, TDFEncoder

        fields = (
            TDFEncoder.encode_string("HOSN", host) +
            TDFEncoder.encode_uint32("PORT", port)
        )

        packet = BlazePacket(
            packet_type=0x00,
            component=0x00,
            command=0x00,
            error_code=0x0000,
            message_id=0x0001,
            payload=fields
        )

        return packet.to_bytes()

    def _journal_connection(self, peer, data):
        journal_logger = logging.getLogger("journal.network")
        entry = {
            "timestamp": time.time(),
            "source": "redirector",
            "peer": f"{peer[0]}:{peer[1]}",
            "direction": "recv",
            "data_hex": data.hex(),
            "data_len": len(data)
        }
        journal_logger.debug(json.dumps(entry))
