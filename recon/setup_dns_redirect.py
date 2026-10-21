"""
DNS Redirect Setup for FIFA 16.

FIFA 16 resolves EA servers via DNS. To redirect the game to a local
server, we modify the Windows hosts file to point EA domains to 127.0.0.1.

Run as Administrator!

Usage:
    python recon/setup_dns_redirect.py install
    python recon/setup_dns_redirect.py remove
    python recon/setup_dns_redirect.py status
"""

import sys
import os
import ctypes
from pathlib import Path

HOSTS_FILE = Path(r"C:\Windows\System32\drivers\etc\hosts")

MARKER_BEGIN = "# FIFA16-REVIVAL-BEGIN"
MARKER_END = "# FIFA16-REVIVAL-END"

EA_DOMAINS = [
    # Primary Blaze redirector — environment-prefixed (the REAL entry point)
    "winter15.gosredirector.ea.com",
    "winter15.gosredirector.sdev.ea.com",
    "winter15.gosredirector.stest.ea.com",
    "winter15.gosredirector.scert.ea.com",
    # Unprefixed variants (also present in binary)
    "gosredirector.ea.com",
    "gosredirector.sdev.ea.com",
    "gosredirector.stest.ea.com",
    "gosredirector.scert.ea.com",
    # Blaze infrastructure
    "gosca.ea.com",
    "scert.ea.com",
    "gateway.ea.com",
    "gateway.int.ea.com",
    # Authentication
    "accounts.ea.com",
    "signin.ea.com",
    "accounts.int.ea.com",
    "signin.int.ea.com",
    # Online services
    "online.ea.com",
    "data.ea.com",
    "eastore.ea.com",
    "worldwide.ea.com",
    "support.ea.com",
    "fifa.easports.com",
    "www.easportsfootball.com",
    # FUT / EA Sports FC web services
    "easportsworld.ea.com",
    "easfc.ea.com",
    "content.lt.easfc.ea.com",
    "pas.gt.easfc.ea.com",
    "easw.easports.com",
    "peach.online.ea.com",
    # Telemetry / diagnostics (quiet-fail usually fine, redirect to be safe)
    "gos.ea.com",
    "elephant.online.ea.com",
    "pin-river.data.ea.com",
    "river.data.ea.com",
    "fifa15.service.easports.com",
    "gen4.reports.tools.gos.ea.com",
]


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def read_hosts():
    with open(HOSTS_FILE, "r", encoding="utf-8") as f:
        return f.read()


def write_hosts(content):
    with open(HOSTS_FILE, "w", encoding="utf-8") as f:
        f.write(content)


def remove_existing_block(content):
    lines = content.split("\n")
    result = []
    inside_block = False

    for line in lines:
        stripped = line.strip()
        if stripped == MARKER_BEGIN:
            inside_block = True
            continue
        if stripped == MARKER_END:
            inside_block = False
            continue
        if not inside_block:
            result.append(line)

    return "\n".join(result)


def install():
    if not is_admin():
        print("ERROR: This script must be run as Administrator.")
        print("Right-click your terminal and select 'Run as administrator'.")
        sys.exit(1)

    content = read_hosts()
    content = remove_existing_block(content)

    block_lines = [MARKER_BEGIN]
    block_lines.append("# FIFA 16 Revival - Redirect EA servers to localhost")
    block_lines.append("# Remove this block by running: python recon/setup_dns_redirect.py remove")
    block_lines.append("")

    for domain in EA_DOMAINS:
        block_lines.append(f"127.0.0.1 {domain}")

    block_lines.append("")
    block_lines.append(MARKER_END)

    block = "\n".join(block_lines)

    if not content.endswith("\n"):
        content += "\n"
    content += block + "\n"

    write_hosts(content)

    print(f"Installed {len(EA_DOMAINS)} DNS redirects to 127.0.0.1")
    print(f"\nRedirected domains:")
    for domain in EA_DOMAINS:
        print(f"  {domain}")

    print(f"\nHosts file modified: {HOSTS_FILE}")
    print("Flush DNS cache: ipconfig /flushdns")


def remove():
    if not is_admin():
        print("ERROR: This script must be run as Administrator.")
        sys.exit(1)

    content = read_hosts()
    cleaned = remove_existing_block(content)
    write_hosts(cleaned)

    print("Removed FIFA 16 Revival DNS redirects from hosts file.")
    print("Flush DNS cache: ipconfig /flushdns")


def status():
    content = read_hosts()

    if MARKER_BEGIN in content:
        print("DNS redirects: INSTALLED")
        print(f"\nRedirected domains:")
        for domain in EA_DOMAINS:
            if domain in content:
                print(f"  {domain} -> 127.0.0.1")
    else:
        print("DNS redirects: NOT INSTALLED")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("Commands: install, remove, status")
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "install":
        install()
    elif command == "remove":
        remove()
    elif command == "status":
        status()
    else:
        print(f"Unknown command: {command}")
        print("Commands: install, remove, status")
        sys.exit(1)


if __name__ == "__main__":
    main()
