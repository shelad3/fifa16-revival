"""
Blaze Authentication Server

Handles the Blaze login flow for FIFA 16:
  1. PreAuth - initial handshake, TLS negotiation
  2. Authentication - login credentials/tokens
  3. PostAuth - session establishment, server config

This is the core of the server - if login works, FUT becomes reachable.
"""

import asyncio
import logging
import json
import time
import uuid
from typing import Dict, Optional

from server.blaze import BlazePacket, BlazeComponent, TDFEncoder, TDFDecoder

log = logging.getLogger("blaze.auth")


class Session:
    """Represents a connected client session."""

    def __init__(self, session_id: int, user_id: int, persona_id: int,
                 display_name: str, addr: tuple):
        self.session_id = session_id
        self.user_id = user_id
        self.persona_id = persona_id
        self.display_name = display_name
        self.addr = addr
        self.created_at = time.time()
        self.last_seen = time.time()
        self.state = "authenticated"
        self.current_match = None

    def to_dict(self):
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "persona_id": self.persona_id,
            "display_name": self.display_name,
            "addr": f"{self.addr[0]}:{self.addr[1]}",
            "state": self.state,
            "created_at": self.created_at
        }


class BlazeAuthServer:
    """Blaze authentication and session server."""

    def __init__(self, config, db):
        self.name = "Blaze Auth Server"
        self.config = config
        self.db = db
        self.server = None
        self.tls_server = None
        self.sessions: Dict[int, Session] = {}
        self.session_counter = 1

    async def start(self):
        self.server = await asyncio.start_server(
            self._handle_client,
            self.config["host"],
            self.config["tcp_port"]
        )
        log.info("Auth server listening on %s:%s",
                 self.config["host"], self.config["tcp_port"])

        if self.config.get("use_tls"):
            await self._start_tls_listener()

    async def _start_tls_listener(self):
        """Optional TLS listener (ssl_port) using a self-signed cert."""
        import ssl
        from pathlib import Path

        cert = Path(self.config.get("cert_file", ""))
        key = Path(self.config.get("key_file", ""))

        if not (cert.is_file() and key.is_file()):
            log.warning("Auth: TLS requested but cert/key missing at %s / %s - "
                        "run tools/gen_cert.py first", cert, key)
            return

        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        try:
            ctx.load_cert_chain(str(cert), str(key))
        except Exception as e:
            log.error("Auth: failed to load TLS cert: %s", e)
            return

        self.tls_server = await asyncio.start_server(
            self._handle_client,
            self.config["host"],
            self.config["ssl_port"],
            ssl=ctx
        )
        log.info("Auth server (TLS) listening on %s:%s",
                 self.config["host"], self.config["ssl_port"])

    async def stop(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        if self.tls_server:
            self.tls_server.close()
            await self.tls_server.wait_closed()

    async def _handle_client(self, reader, writer):
        peer = writer.get_extra_info("peername")
        log.info("Auth: new connection from %s:%s", peer[0], peer[1])

        current_session: Optional[Session] = None

        try:
            while True:
                header = await asyncio.wait_for(reader.readexactly(8), timeout=30.0)

                packet_type = int.from_bytes(header[0:2], "big")
                component = header[2]
                command = header[3]
                error_code = int.from_bytes(header[4:6], "big")
                message_id = int.from_bytes(header[6:8], "big")

                payload_len_bytes = await asyncio.wait_for(
                    reader.readexactly(4), timeout=10.0
                )
                payload_len = int.from_bytes(payload_len_bytes, "big")

                if payload_len > 10_000_000:
                    log.warning("Auth: implausible payload_len=%d from %s - "
                                "journaling and closing", payload_len, peer)
                    break

                payload = b""
                if payload_len > 0:
                    payload = await asyncio.wait_for(
                        reader.readexactly(payload_len), timeout=10.0
                    )

                packet = BlazePacket(
                    packet_type=packet_type,
                    component=component,
                    command=command,
                    error_code=error_code,
                    message_id=message_id,
                    payload=payload
                )

                self._journal_packet(peer, "recv", packet)

                response = await self._dispatch_packet(packet, peer, current_session)

                if response:
                    sess = getattr(response, "_session", None)
                    if sess is not None:
                        current_session = sess
                    writer.write(response.to_bytes())
                    await writer.drain()
                    self._journal_packet(peer, "send", response)

                if getattr(response, "_close_after_send", False):
                    break

        except asyncio.IncompleteReadError:
            log.info("Auth: connection closed by %s", peer)
        except asyncio.TimeoutError:
            log.warning("Auth: timeout from %s", peer)
        except ConnectionResetError:
            log.info("Auth: connection reset by %s", peer)
        except Exception as e:
            log.error("Auth: error with %s: %s", peer, e, exc_info=True)
        finally:
            if current_session:
                self.sessions.pop(current_session.session_id, None)
                log.info("Auth: session %d closed for %s",
                         current_session.session_id, peer)
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def _dispatch_packet(self, packet: BlazePacket, peer, session):
        comp_name = (BlazeComponent(packet.component).name
                     if packet.component in BlazeComponent
                     else f"0x{packet.component:02X}")

        log.debug("Auth: %s cmd=0x%02X msg_id=%d",
                  comp_name, packet.command, packet.message_id)

        handler_map = {
            (BlazeComponent.AUTHENTICATION, 0x00): self._handle_preauth,
            (BlazeComponent.AUTHENTICATION, 0x01): self._handle_auth,
            (BlazeComponent.AUTHENTICATION, 0x02): self._handle_postauth,
            (BlazeComponent.AUTHENTICATION, 0x03): self._handle_user_settings,
            (BlazeComponent.UTIL, 0x00): self._handle_get_ping,
            (BlazeComponent.UTIL, 0x01): self._handle_update_network_info,
            (BlazeComponent.UTIL, 0x04): self._handle_get_config,
            (BlazeComponent.UTIL, 0x12): self._handle_pre_auth_msg,
            (BlazeComponent.UTIL, 0x13): self._handle_post_auth_msg,
            (BlazeComponent.USER_SESSIONS, 0x00): self._handle_get_session,
            (BlazeComponent.USER_SESSIONS, 0x03): self._handle_update_session,
            (BlazeComponent.USER_SESSIONS, 0x04): self._handle_update_player_data,
        }

        handler = handler_map.get((packet.component, packet.command))

        if handler:
            return await handler(packet, peer, session)
        else:
            return self._handle_unknown(packet, peer, session)

    async def _handle_preauth(self, packet, peer, session):
        """Handle PreAuth - initial client handshake."""
        log.info("Auth: PreAuth from %s", peer)

        decoded = TDFDecoder.decode(packet.payload)
        for val in decoded:
            log.debug("  PreAuth field: %s = %s", val.name, val.value)

        fields = (
            TDFEncoder.encode_uint64("AUID", 1001) +
            TDFEncoder.encode_uint64("SPID", 2001) +
            TDFEncoder.encode_string("PUID", "player_1001") +
            TDFEncoder.encode_uint64("SIDN", 1) +
            TDFEncoder.encode_string("SESS", str(uuid.uuid4()))
        )

        return BlazePacket(
            packet_type=0x00,
            component=BlazeComponent.AUTHENTICATION,
            command=0x00,
            error_code=0x0000,
            message_id=packet.message_id,
            payload=fields
        )

    async def _handle_auth(self, packet, peer, session):
        """Handle Authentication - login with credentials."""
        log.info("Auth: Authentication from %s", peer)

        decoded = TDFDecoder.decode(packet.payload)
        username = "Player"
        for val in decoded:
            log.debug("  Auth field: %s = %s", val.name, val.value)
            if val.name in ("NAME", "PUID"):
                username = str(val.value)

        user = await self.db.get_or_create_user(username)
        persona = await self.db.get_default_persona(user["id"])

        session_id = self.session_counter
        self.session_counter += 1

        current_session = Session(
            session_id=session_id,
            user_id=user["id"],
            persona_id=persona["id"],
            display_name=persona["display_name"],
            addr=peer
        )
        self.sessions[session_id] = current_session

        fields = (
            TDFEncoder.encode_uint64("AUID", user["id"]) +
            TDFEncoder.encode_uint64("SPID", persona["id"]) +
            TDFEncoder.encode_string("PKEY", str(uuid.uuid4()))
        )

        response = BlazePacket(
            packet_type=0x00,
            component=BlazeComponent.AUTHENTICATION,
            command=0x01,
            error_code=0x0000,
            message_id=packet.message_id,
            payload=fields
        )
        response._session = current_session
        return response

    async def _handle_postauth(self, packet, peer, session):
        """Handle PostAuth - establish session, send server config."""
        log.info("Auth: PostAuth from %s", peer)

        fut_api_host = self.config.get("fut_api_host", "127.0.0.1")
        fut_api_port = self.config.get("fut_api_port", 42129)

        fields = (
            TDFEncoder.encode_string("SIDN", "1") +
            TDFEncoder.encode_uint32("SPRT", 0) +
            TDFEncoder.encode_struct("SKEY", 
                TDFEncoder.encode_string("KVAL", str(uuid.uuid4()))
            ) +
            TDFEncoder.encode_string("APIT", "FUT") +
            TDFEncoder.encode_string("HOST", fut_api_host) +
            TDFEncoder.encode_uint32("PORT", fut_api_port)
        )

        return BlazePacket(
            packet_type=0x00,
            component=BlazeComponent.AUTHENTICATION,
            command=0x02,
            error_code=0x0000,
            message_id=packet.message_id,
            payload=fields
        )

    async def _handle_user_settings(self, packet, peer, session):
        """Handle user settings update."""
        log.info("Auth: UserSettings from %s", peer)
        return BlazePacket(
            packet_type=0x00,
            component=BlazeComponent.AUTHENTICATION,
            command=0x03,
            error_code=0x0000,
            message_id=packet.message_id,
            payload=b""
        )

    async def _handle_get_ping(self, packet, peer, session):
        """Handle Util.GetPingServers"""
        log.debug("Auth: GetPing from %s", peer)
        ping_host = self.config.get("host", "127.0.0.1")
        ping_port = self.config.get("tcp_port", 42230)

        fields = (
            TDFEncoder.encode_list("SRLS", "STRC", [
                TDFEncoder.encode_struct("",
                    TDFEncoder.encode_string("HOSN", ping_host) +
                    TDFEncoder.encode_uint32("PORT", ping_port) +
                    TDFEncoder.encode_string("PLAT", "PC")
                )
            ])
        )

        return BlazePacket(
            packet_type=0x00,
            component=BlazeComponent.UTIL,
            command=0x00,
            error_code=0x0000,
            message_id=packet.message_id,
            payload=fields
        )

    async def _handle_update_network_info(self, packet, peer, session):
        """Handle Util.UpdateNetworkInfo - client reports its IP."""
        log.debug("Auth: UpdateNetworkInfo from %s", peer)
        return BlazePacket(
            packet_type=0x00,
            component=BlazeComponent.UTIL,
            command=0x01,
            error_code=0x0000,
            message_id=packet.message_id,
            payload=b""
        )

    async def _handle_get_config(self, packet, peer, session):
        """Handle Util.GetConfig - server configuration."""
        log.debug("Auth: GetConfig from %s", peer)

        fields = (
            TDFEncoder.encode_string("APIT", "FUT") +
            TDFEncoder.encode_string("SVER", "1.0")
        )

        return BlazePacket(
            packet_type=0x00,
            component=BlazeComponent.UTIL,
            command=0x04,
            error_code=0x0000,
            message_id=packet.message_id,
            payload=fields
        )

    async def _handle_pre_auth_msg(self, packet, peer, session):
        """Handle Util.PreAuthMessage"""
        log.debug("Auth: PreAuthMessage from %s", peer)
        return BlazePacket(
            packet_type=0x00,
            component=BlazeComponent.UTIL,
            command=0x12,
            error_code=0x0000,
            message_id=packet.message_id,
            payload=b""
        )

    async def _handle_post_auth_msg(self, packet, peer, session):
        """Handle Util.PostAuthMessage"""
        log.debug("Auth: PostAuthMessage from %s", peer)
        return BlazePacket(
            packet_type=0x00,
            component=BlazeComponent.UTIL,
            command=0x13,
            error_code=0x0000,
            message_id=packet.message_id,
            payload=b""
        )

    async def _handle_get_session(self, packet, peer, session):
        """Handle UserSessions.GetSession"""
        log.debug("Auth: GetSession from %s", peer)
        fields = TDFEncoder.encode_uint64("SESS", session.session_id if session else 0)
        return BlazePacket(
            packet_type=0x00,
            component=BlazeComponent.USER_SESSIONS,
            command=0x00,
            error_code=0x0000,
            message_id=packet.message_id,
            payload=fields
        )

    async def _handle_update_session(self, packet, peer, session):
        """Handle UserSessions.UpdateSession"""
        log.debug("Auth: UpdateSession from %s", peer)
        return BlazePacket(
            packet_type=0x00,
            component=BlazeComponent.USER_SESSIONS,
            command=0x03,
            error_code=0x0000,
            message_id=packet.message_id,
            payload=b""
        )

    async def _handle_update_player_data(self, packet, peer, session):
        """Handle UserSessions.UpdatePlayerData"""
        log.debug("Auth: UpdatePlayerData from %s", peer)
        return BlazePacket(
            packet_type=0x00,
            component=BlazeComponent.USER_SESSIONS,
            command=0x04,
            error_code=0x0000,
            message_id=packet.message_id,
            payload=b""
        )

    def _handle_unknown(self, packet, peer, session):
        """Handle unknown commands - log for reverse engineering."""
        unknown_logger = logging.getLogger("journal.unknown")
        unknown_logger.debug(
            "UNKNOWN: component=0x%02X command=0x%02X msg_id=%d payload_len=%d payload_hex=%s",
            packet.component, packet.command, packet.message_id,
            len(packet.payload), packet.payload.hex()
        )

        log.warning("Auth: unknown command comp=0x%02X cmd=0x%02X from %s",
                    packet.component, packet.command, peer)

        return BlazePacket(
            packet_type=0x00,
            component=packet.component,
            command=packet.command,
            error_code=0x0000,
            message_id=packet.message_id,
            payload=b""
        )

    def _journal_packet(self, peer, direction, packet):
        journal_logger = logging.getLogger("journal.network")
        entry = {
            "timestamp": time.time(),
            "source": "auth_server",
            "peer": f"{peer[0]}:{peer[1]}",
            "direction": direction,
            "packet_type": packet.packet_type,
            "component": packet.component,
            "command": packet.command,
            "error_code": packet.error_code,
            "message_id": packet.message_id,
            "payload_len": len(packet.payload),
            "payload_hex": packet.payload.hex()
        }
        journal_logger.debug(json.dumps(entry))
