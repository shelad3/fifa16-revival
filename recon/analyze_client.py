"""
FIFA 16 Client Analysis Tool.

Scans the FIFA 16 installation directory for network-related strings,
server URLs, and configuration files. Helps identify what endpoints
the client expects.

Usage:
    python recon/analyze_client.py "C:\\Program Files\\EA Sports\\FIFA 16"
    python recon/analyze_client.py "D:\\Games\\FIFA16" --output recon/client_findings.json
"""

import argparse
import json
import re
import sys
from pathlib import Path

EA_PATTERNS = [
    rb'https?://[a-zA-Z0-9._/-]+ea\.com[a-zA-Z0-9._/-]*',
    rb'https?://[a-zA-Z0-9._/-]+\.ea\.com',
    rb'[a-z0-9-]+\.ea\.com',
    rb'ff-nrt[a-zA-Z0-9._-]*',
    rb'utas[a-zA-Z0-9._-]*',
    rb'blaze[a-zA-Z0-9._-]*',
    rb'gameservices[a-zA-Z0-9._-]*',
]

PORT_PATTERNS = [
    rb'42127',
    rb'42133',
    rb'42230',
    rb'443',
    rb'3659',
]

NETWORK_FILE_EXTENSIONS = {'.exe', '.dll', '.ini', '.cfg', '.xml', '.json', '.dat', '.bin'}


def scan_file_for_strings(filepath, patterns):
    results = []
    try:
        data = filepath.read_bytes()
    except (PermissionError, OSError):
        return results

    for pattern in patterns:
        for match in re.finditer(pattern, data):
            try:
                s = match.group().decode('ascii', errors='ignore')
                if s and len(s) > 3:
                    offset = match.start()
                    context = data[max(0, offset-20):min(len(data), offset+len(s)+20)]
                    results.append({
                        'file': str(filepath),
                        'offset': offset,
                        'match': s,
                        'context_hex': context.hex()[:100]
                    })
            except Exception:
                continue

    return results


def analyze_install(install_path):
    install = Path(install_path)

    if not install.exists():
        print(f"Error: Path does not exist: {install}")
        sys.exit(1)

    print(f"Scanning: {install}")
    print("=" * 60)

    all_results = {
        'urls': [],
        'domains': [],
        'ports': [],
        'files_scanned': 0,
        'config_files': [],
    }

    files_to_scan = []

    for filepath in install.rglob("*"):
        if not filepath.is_file():
            continue
        if filepath.suffix.lower() not in NETWORK_FILE_EXTENSIONS:
            continue
        if filepath.stat().st_size > 50 * 1024 * 1024:
            continue
        files_to_scan.append(filepath)

    print(f"Found {len(files_to_scan)} files to scan")

    for filepath in files_to_scan:
        all_results['files_scanned'] += 1

        if filepath.suffix.lower() in ('.ini', '.cfg', '.xml', '.json'):
            all_results['config_files'].append(str(filepath))
            try:
                text = filepath.read_text(encoding='utf-8', errors='ignore')
                for line in text.split('\n'):
                    if 'ea.com' in line.lower() or 'http' in line.lower():
                        print(f"\n  CONFIG: {filepath.name}")
                        print(f"    {line.strip()}")
            except Exception:
                pass

        found = scan_file_for_strings(filepath, EA_PATTERNS + PORT_PATTERNS)

        for r in found:
            match = r['match']
            if 'ea.com' in match or match.startswith('http'):
                if not any(existing['match'] == match for existing in all_results['urls']):
                    all_results['urls'].append(r)
                    print(f"\n  URL: {match}")
                    print(f"    File: {filepath.name} @ 0x{r['offset']:X}")
            elif '.' in match and 'ea' in match:
                if not any(existing['match'] == match for existing in all_results['domains']):
                    all_results['domains'].append(r)
                    print(f"\n  Domain: {match}")
                    print(f"    File: {filepath.name} @ 0x{r['offset']:X}")

    print(f"\n{'=' * 60}")
    print(f"Summary:")
    print(f"  Files scanned: {all_results['files_scanned']}")
    print(f"  URLs found: {len(all_results['urls'])}")
    print(f"  Domains found: {len(all_results['domains'])}")
    print(f"  Config files: {len(all_results['config_files'])}")

    if all_results['urls']:
        print(f"\nAll EA URLs:")
        for r in all_results['urls']:
            print(f"  {r['match']}")

    return all_results


def main():
    parser = argparse.ArgumentParser(description="Analyze FIFA 16 client for network endpoints")
    parser.add_argument("install_path", help="Path to FIFA 16 installation")
    parser.add_argument("--output", help="Save results to JSON file")
    args = parser.parse_args()

    results = analyze_install(args.install_path)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    main()
