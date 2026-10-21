"""
Smoke test for the FIFA 16 Revival Server.

Verifies that all modules import correctly, the database initializes,
and the server starts up without errors.

Usage:
    python tests/test_smoke.py
"""

import asyncio
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def test_imports():
    print("[1/5] Testing imports...")
    try:
        from server.blaze import BlazePacket, BlazeComponent, TDFEncoder, TDFDecoder
        from server.blaze.redirector import BlazeRedirector
        from server.blaze.auth_server import BlazeAuthServer
        from server.fut_api.app import FUTApiServer
        from server.database.db import Database
        from server.logging_setup import setup_logging
        print("      All imports OK")
        return True
    except ImportError as e:
        print(f"      Import FAILED: {e}")
        return False


def test_tdf_encoder():
    print("[2/5] Testing TDF encoder...")
    try:
        from server.blaze import TDFEncoder

        s = TDFEncoder.encode_string("TEST", "hello")
        assert s[:3] == b"TES", "String name encoding failed"
        assert s[3:7] == b"STR\x00", "String type encoding failed"

        i = TDFEncoder.encode_int32("NUM", 42)
        assert i[3:7] == b"I32\x00", "Int32 type encoding failed"

        b = TDFEncoder.encode_bool("FLAG", True)
        assert b[-1] == 0x01, "Bool encoding failed"

        print("      TDF encoder OK")
        return True
    except Exception as e:
        print(f"      TDF encoder FAILED: {e}")
        return False


def test_blaze_packet():
    print("[3/5] Testing Blaze packet...")
    try:
        from server.blaze import BlazePacket

        packet = BlazePacket(
            packet_type=0x00,
            component=0x00,
            command=0x01,
            error_code=0x0000,
            message_id=1,
            payload=b"\x00" * 10
        )

        data = packet.to_bytes()
        assert len(data) == 12 + 10, f"Packet size wrong: {len(data)}"

        parsed = BlazePacket.from_bytes(data)
        assert parsed is not None, "Failed to parse packet"
        assert parsed.component == 0x00, "Component mismatch"
        assert parsed.command == 0x01, "Command mismatch"
        assert len(parsed.payload) == 10, "Payload length mismatch"

        print("      Blaze packet OK")
        return True
    except Exception as e:
        print(f"      Blaze packet FAILED: {e}")
        return False


async def test_database():
    print("[4/5] Testing database...")
    db = None
    try:
        from server.database.db import Database

        tmpdir = tempfile.mkdtemp()
        db_path = str(Path(tmpdir) / "test.db")
        db = Database({"path": db_path})
        await db.initialize()

        user = await db.get_or_create_user("test_player")
        assert user["id"] > 0, "User creation failed"

        club = await db.get_or_create_club(user["id"])
        assert club["credits"] == 10000, "Club credits wrong"

        players = await db.get_players(limit=5)
        assert len(players) > 0, "No players in catalog"

        item = await db.add_item(user["id"], players[0]["definition_id"])
        assert item["item_id"], "Item creation failed"

        items = await db.get_user_items(user["id"])
        assert len(items) == 1, "Item retrieval failed"

        pack_items = await db.generate_pack_contents(user["id"])
        assert len(pack_items) > 0, "Pack generation failed"

        await db.close()
        db = None

        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)

        print("      Database OK")
        return True
    except Exception as e:
        print(f"      Database FAILED: {e}")
        import traceback
        traceback.print_exc()
        if db:
            try:
                await db.close()
            except Exception:
                pass
        return False


def test_config():
    print("[5/5] Testing configuration...")
    try:
        config_path = Path(__file__).parent.parent / "config" / "server_config.json"
        with open(config_path, "r") as f:
            config = json.load(f)

        assert "blaze" in config, "Missing blaze config"
        assert "fut_api" in config, "Missing fut_api config"
        assert "database" in config, "Missing database config"
        assert config["blaze"]["redirector_port"] == 42127, "Wrong redirector port"

        print("      Config OK")
        return True
    except Exception as e:
        print(f"      Config FAILED: {e}")
        return False


def main():
    print("=" * 50)
    print("  FIFA 16 Revival Server - Smoke Test")
    print("=" * 50)
    print()

    results = [
        test_imports(),
        test_tdf_encoder(),
        test_blaze_packet(),
        asyncio.run(test_database()),
        test_config(),
    ]

    print()
    print("=" * 50)

    passed = sum(results)
    total = len(results)

    if passed == total:
        print(f"  ALL {total} TESTS PASSED")
        print("=" * 50)
        sys.exit(0)
    else:
        print(f"  {total - passed}/{total} TESTS FAILED")
        print("=" * 50)
        sys.exit(1)


if __name__ == "__main__":
    main()
