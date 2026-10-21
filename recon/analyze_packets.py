"""
Packet Capture Analyzer for FIFA 16.

Reads network journal JSONL files produced by the server and provides
analysis of Blaze traffic patterns. Useful for reverse engineering.

Usage:
    python recon/analyze_packets.py logs/network_journal.jsonl
    python recon/analyze_packets.py logs/network_journal.jsonl --component 0x00
"""

import json
import sys
import argparse
from collections import defaultdict, Counter
from pathlib import Path

BLAZE_COMPONENTS = {
    0x00: "Authentication",
    0x01: "GameManager",
    0x02: "UserSessions",
    0x03: "Presence",
    0x04: "Friends",
    0x05: "Gameplay",
    0x06: "Stats",
    0x07: "Messaging",
    0x08: "Gameroom",
    0x09: "GameReporting",
    0x0A: "Util",
    0x0B: "Clubs",
    0x0C: "Channels",
}

KNOWN_COMMANDS = {
    (0x00, 0x00): "PreAuth",
    (0x00, 0x01): "Authentication",
    (0x00, 0x02): "PostAuth",
    (0x00, 0x03): "UserSettings",
    (0x0A, 0x00): "GetPingServers",
    (0x0A, 0x01): "UpdateNetworkInfo",
    (0x0A, 0x04): "GetConfig",
    (0x0A, 0x12): "PreAuthMessage",
    (0x0A, 0x13): "PostAuthMessage",
    (0x02, 0x00): "GetSession",
    (0x02, 0x03): "UpdateSession",
    (0x02, 0x04): "UpdatePlayerData",
}


def load_journal(path):
    entries = []
    with open(path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                print(f"Warning: invalid JSON on line {line_num}")
    return entries


def analyze(entries, component_filter=None):
    print("=" * 70)
    print("  FIFA 16 Network Traffic Analysis")
    print("=" * 70)

    recv_packets = [e for e in entries if e.get("direction") == "recv"]
    send_packets = [e for e in entries if e.get("direction") == "send"]

    print(f"\nTotal entries: {len(entries)}")
    print(f"Received: {len(recv_packets)}")
    print(f"Sent: {len(send_packets)}")

    if not recv_packets and not send_packets:
        print("\nNo directional packets found. Checking for raw entries...")
        raw = [e for e in entries if "data_hex" in e]
        print(f"Raw data entries: {len(raw)}")
        return

    print(f"\n{'─' * 70}")
    print("PACKET DISTRIBUTION BY COMPONENT")
    print(f"{'─' * 70}")

    component_recv = Counter()
    component_send = Counter()

    for e in recv_packets:
        comp = e.get("component", 0)
        if component_filter and comp != component_filter:
            continue
        component_recv[comp] += 1

    for e in send_packets:
        comp = e.get("component", 0)
        if component_filter and comp != component_filter:
            continue
        component_send[comp] += 1

    all_components = sorted(set(list(component_recv.keys()) + list(component_send.keys())))

    for comp in all_components:
        name = BLAZE_COMPONENTS.get(comp, f"Unknown(0x{comp:02X})")
        print(f"\n  Component 0x{comp:02X} ({name}):")
        print(f"    Recv: {component_recv.get(comp, 0):>5}  Send: {component_send.get(comp, 0):>5}")

    print(f"\n{'─' * 70}")
    print("COMMAND ANALYSIS")
    print(f"{'─' * 70}")

    command_analysis = defaultdict(lambda: {"recv": 0, "send": 0, "payload_lens": []})

    for e in entries:
        comp = e.get("component", 0)
        cmd = e.get("command", 0)
        direction = e.get("direction", "unknown")
        payload_len = e.get("payload_len", 0)

        if component_filter and comp != component_filter:
            continue

        key = (comp, cmd)
        command_analysis[key][direction] += 1
        command_analysis[key]["payload_lens"].append(payload_len)

    for (comp, cmd), data in sorted(command_analysis.items()):
        comp_name = BLAZE_COMPONENTS.get(comp, f"0x{comp:02X}")
        cmd_name = KNOWN_COMMANDS.get((comp, cmd), "UNKNOWN")

        avg_payload = (sum(data["payload_lens"]) / len(data["payload_lens"])
                       if data["payload_lens"] else 0)

        marker = " ⚠" if cmd_name == "UNKNOWN" else ""

        print(f"\n  {comp_name}.cmd=0x{cmd:02X} ({cmd_name}){marker}")
        print(f"    Recv: {data['recv']:>5}  Send: {data['send']:>5}  "
              f"Avg payload: {avg_payload:.0f} bytes")

    unknown = [(c, cmd) for (c, cmd), d in command_analysis.items()
               if (c, cmd) not in KNOWN_COMMANDS]

    if unknown:
        print(f"\n{'─' * 70}")
        print(f"UNKNOWN COMMANDS ({len(unknown)}) — These need reverse engineering!")
        print(f"{'─' * 70}")
        for comp, cmd in sorted(unknown):
            name = BLAZE_COMPONENTS.get(comp, f"0x{comp:02X}")
            print(f"  {name} (0x{comp:02X}).cmd=0x{cmd:02X}")

    print(f"\n{'─' * 70}")
    print("PAYLOAD PATTERNS (Hex Samples)")
    print(f"{'─' * 70}")

    seen = set()
    for e in entries[:50]:
        comp = e.get("component", 0)
        cmd = e.get("command", 0)
        key = (comp, cmd)
        if key in seen:
            continue
        seen.add(key)

        payload_hex = e.get("payload_hex", e.get("data_hex", ""))
        if payload_hex:
            comp_name = BLAZE_COMPONENTS.get(comp, f"0x{comp:02X}")
            cmd_name = KNOWN_COMMANDS.get((comp, cmd), "?")
            print(f"\n  {comp_name}.cmd=0x{cmd:02X} ({cmd_name}):")
            print(f"    {payload_hex[:120]}{'...' if len(payload_hex) > 120 else ''}")


def main():
    parser = argparse.ArgumentParser(description="Analyze FIFA 16 Blaze network traffic")
    parser.add_argument("journal_file", help="Path to network journal JSONL file")
    parser.add_argument("--component", help="Filter by component ID (hex, e.g. 0x00)")
    args = parser.parse_args()

    path = Path(args.journal_file)
    if not path.exists():
        print(f"Error: File not found: {path}")
        sys.exit(1)

    component_filter = None
    if args.component:
        component_filter = int(args.component, 16)

    entries = load_journal(path)
    analyze(entries, component_filter)


if __name__ == "__main__":
    main()
