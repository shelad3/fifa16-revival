"""
Blaze Redirector Server

First server the FIFA 16 client contacts. Speaks TWO protocols on the
same port (42127), because the real winter15 redirector supports both:

  1. Classic Blaze TCP: 4-byte length prefix + TDF payload
  2. HTTP: the client's ProtoHttp fallback (X-BLAZE-ERRORCODE flow)

Everything received is journalled byte-for-byte for reverse engineering.
"""

import asyncio
import logging
import json
import time

log = logging.getLogger("blaze.redirector")

HTTP_PREFIXES = (b"GET ", b"POST ", b"HEAD ", b"PUT ", b"DELETE ", b"OPTIONS ")


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
        log.info("Redirector listening on %s:%s (Blaze TCP + HTTP)", self.host, self.port)

    async def stop(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()

    async def _handle_client(self, reader, writer):
        peer = writer.get_extra_info("peername")
        log.info("Redirector: new connection from %s:%s", peer[0], peer[1])

        try:
            data = await asyncio.wait_for(reader.read(8192), timeout=15.0)

            if not data:
                log.warning("Redirector: empty connection from %s", peer)
                writer.close()
                return

            self._journal_connection(peer, data)

            if data.startswith(HTTP_PREFIXES):
                response = self._build_http_response(data, peer)
            else:
                response = self._build_blaze_response(data, peer)

            writer.write(response)
            await writer.drain()

            log.info("Redirector: replied to %s (%d bytes)", peer, len(response))

        except asyncio.TimeoutError:
            log.warning("Redirector: timeout from %s", peer)
        except Exception as e:
            log.error("Redirector: error handling %s: %s", peer, e, exc_info=True)
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    def _redirect_target(self):
        host = self.config.get("auth_host", "127.0.0.1")
        # Try SSL port first since client is attempting TLS
        port = self.config.get("ssl_port", 42133)
        return host, port

    def _build_blaze_response(self, request: bytes, peer) -> bytes:
        """Classic Blaze redirect: TDF with hostname + port of the auth server."""
        from server.blaze import BlazePacket, TDFEncoder

        host, port = self._redirect_target()

        fields = (
            TDFEncoder.encode_struct("DATA",
                TDFEncoder.encode_string("HOSN", host) +
                TDFEncoder.encode_uint32("PORT", port) +
                TDFEncoder.encode_uint32("TYPE", 0)
            )
        )

        packet = BlazePacket(
            packet_type=0x00,
            component=0x00,
            command=0x00,
            error_code=0x0000,
            message_id=0x0001,
            payload=fields
        )

        payload = packet.to_bytes()
        return len(payload).to_bytes(4, "big") + payload

    def _build_http_response(self, request: bytes, peer) -> bytes:
        """HTTP fallback response - XML server list (best guess, journaled)."""
        host, port = self._redirect_target()

        first_line = request.split(b"\r\n", 1)[0].decode("ascii", "replace")
        log.info("Redirector: HTTP request from %s: %s", peer, first_line)

        body = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            "<servers>\n"
            f"  <server><hostname>{host}</hostname><port>{port}</port>"
            "<type>0</type><status>1</status></server>\n"
            "</servers>\n"
        ).encode("utf-8")

        headers = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: application/xml\r\n"
            f"Content-Length: {len(body)}\r\n"
            "Connection: close\r\n"
            "\r\n"
        ).encode("ascii")

        return headers + body

    def _journal_connection(self, peer, data):
        journal_logger = logging.getLogger("journal.network")
        entry = {
            "timestamp": time.time(),
            "source": "redirector",
            "peer": f"{peer[0]}:{peer[1]}",
            "direction": "recv",
            "data_hex": data[:4096].hex(),
            "data_len": len(data),
            "ascii_preview": data[:200].decode("ascii", "replace")
        }
        journal_logger.debug(json.dumps(entry))
