"""
FIFA 16 Binary Patch Helper.

Provides utilities for patching the FIFA 16 executable to:
  1. Redirect server addresses to localhost
  2. Disable TLS certificate verification
  3. Force connection to custom servers

IMPORTANT: Always run backup_game.py first!

Usage:
    python tools/patch_client.py --scan "C:\\Games\\FIFA16"
    python tools/patch_client.py --patch-redirect "C:\\Games\\FIFA16" --server-ip 127.0.0.1
"""

import argparse
import struct
import sys
from pathlib import Path

KNOWN_PATTERNS = {
    "ea_url_1": {
        "pattern": b"https://ff-nrt-r3.fifa16.ea.com",
        "description": "Blaze redirector URL",
    },
    "ea_url_2": {
        "pattern": b"ff-nrt-r3.fifa16.ea.com",
        "description": "Blaze redirector hostname",
    },
    "ea_url_3": {
        "pattern": b"utas.fut.ea.com",
        "description": "FUT HTTP API hostname",
    },
    "ea_url_4": {
        "pattern": b"accounts.ea.com",
        "description": "EA Accounts hostname",
    },
    "ea_url_5": {
        "pattern": b"gateway.ea.com",
        "description": "EA Gateway hostname",
    },
}


def scan_binary(filepath):
    print(f"Scanning: {filepath}")
    print("=" * 60)

    data = filepath.read_bytes()
    findings = []

    for name, info in KNOWN_PATTERNS.items():
        offset = 0
        while True:
            pos = data.find(info["pattern"], offset)
            if pos == -1:
                break

            context = data[max(0, pos-16):min(len(data), pos+len(info["pattern"])+16)]

            findings.append({
                "name": name,
                "description": info["description"],
                "offset": pos,
                "pattern_len": len(info["pattern"]),
                "context_hex": context.hex()
            })

            print(f"\n  Found: {info['description']}")
            print(f"    Offset: 0x{pos:08X} ({pos})")
            print(f"    Pattern: {info['pattern'][:60]}...")
            print(f"    Context: {context.hex()[:80]}...")

            offset = pos + 1

    if not findings:
        print("\n  No known EA URL patterns found in this binary.")
        print("  This may mean:")
        print("    - The URLs are in a different file (check .ini, .cfg, or data files)")
        print("    - The binary uses encrypted/obfuscated strings")
        print("    - FIFA 16 uses a different domain structure")

    print(f"\n{'=' * 60}")
    print(f"Total findings: {len(findings)}")

    return findings


def patch_redirect(install_path, server_ip="127.0.0.1", server_port=42127):
    """
    Patch the FIFA 16 client to redirect Blaze connections to our server.

    Strategy: Find EA domain strings in the binary and replace them
    with localhost addresses (padded with null bytes).
    """
    install = Path(install_path)

    candidates = [
        install / "fifa16.exe",
        install / "FIFA16.exe",
    ]

    target = None
    for c in candidates:
        if c.exists():
            target = c
            break

    if not target:
        print("Error: fifa16.exe not found. Check the install path.")
        sys.exit(1)

    print(f"Target: {target}")
    print(f"Server: {server_ip}:{server_port}")

    data = bytearray(target.read_bytes())

    replacements = [
        (b"ff-nrt-r3.fifa16.ea.com", server_ip.encode().ljust(25, b"\x00")),
        (b"utas.fut.ea.com", server_ip.encode().ljust(16, b"\x00")),
    ]

    patched = 0
    for old, new in replacements:
        offset = 0
        while True:
            pos = data.find(old, offset)
            if pos == -1:
                break

            if len(new) > len(old):
                print(f"\n  WARNING: Replacement longer than original for {old}")
                print(f"    Original: {len(old)} bytes")
                print(f"    Replacement: {len(new)} bytes")
                print(f"    Skipping (would corrupt binary)")
                offset = pos + 1
                continue

            padded_new = new[:len(old)].ljust(len(old), b"\x00")
            data[pos:pos+len(old)] = padded_new
            patched += 1
            print(f"\n  Patched at 0x{pos:08X}:")
            print(f"    {old} -> {padded_new}")

            offset = pos + len(old)

    if patched > 0:
        backup_path = target.with_suffix(".exe.original")
        if not backup_path.exists():
            target.rename(backup_path)
            print(f"\n  Original backed up to: {backup_path}")
            target.write_bytes(bytes(data))
            print(f"  Patched file written: {target}")
        else:
            print(f"\n  Backup already exists: {backup_path}")
            print(f"  Overwriting {target}...")
            target.write_bytes(bytes(data))
    else:
        print("\n  No patches applied. Binary may use a different addressing scheme.")
        print("  Consider using a hosts file redirect instead (setup_dns_redirect.py)")


def main():
    parser = argparse.ArgumentParser(description="FIFA 16 binary patching tools")
    parser.add_argument("--scan", help="Scan binary for EA URL patterns")
    parser.add_argument("--patch-redirect", help="Patch binary to redirect to local server")
    parser.add_argument("--server-ip", default="127.0.0.1", help="Local server IP")
    parser.add_argument("--server-port", type=int, default=42127, help="Local server port")
    args = parser.parse_args()

    if args.scan:
        scan_binary(Path(args.scan))
    elif args.patch_redirect:
        patch_redirect(args.patch_redirect, args.server_ip, args.server_port)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
