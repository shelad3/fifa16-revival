"""
FIFA 16 Client Backup & Patch Helper.

Creates backups of game files before modification and provides
utilities for binary patching (e.g., redirecting server addresses,
patching TLS checks).

ALWAYS run backup before any modification!

Usage:
    python tools/backup_game.py "C:\\Program Files\\EA Sports\\FIFA 16"
    python tools/backup_game.py "C:\\Program Files\\EA Sports\\FIFA 16" --restore
"""

import argparse
import hashlib
import json
import shutil
import sys
import time
from pathlib import Path

BACKUP_DIR = "backups"
MANIFEST_FILE = "backup_manifest.json"

CRITICAL_FILES = [
    "fifa16.exe",
    "fifa16.exe.bak",
    "Game\\data\\pc\\locale\\en_US\\loc\\loc_eng.txt",
]

NETWORK_RELATED_PATTERNS = [
    "*.ini",
    "*.cfg",
    "*.xml",
    "*.json",
]


def hash_file(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def create_backup(install_path):
    install = Path(install_path)
    if not install.exists():
        print(f"Error: Install path not found: {install}")
        sys.exit(1)

    backup_root = Path(BACKUP_DIR) / f"fifa16_{int(time.time())}"
    backup_root.mkdir(parents=True, exist_ok=True)

    manifest = {
        "created_at": time.time(),
        "install_path": str(install),
        "backup_path": str(backup_root),
        "files": []
    }

    files_to_backup = []

    for name in CRITICAL_FILES:
        filepath = install / name
        if filepath.exists():
            files_to_backup.append(filepath)

    for pattern in NETWORK_RELATED_PATTERNS:
        for filepath in install.rglob(pattern):
            if filepath.is_file() and filepath.stat().st_size < 10 * 1024 * 1024:
                files_to_backup.append(filepath)

    exe = install / "fifa16.exe"
    if exe.exists():
        files_to_backup.append(exe)

    print(f"Backing up {len(files_to_backup)} files to {backup_root}...")

    for filepath in files_to_backup:
        rel_path = filepath.relative_to(install)
        backup_file = backup_root / rel_path
        backup_file.parent.mkdir(parents=True, exist_ok=True)

        shutil.copy2(filepath, backup_file)

        manifest["files"].append({
            "original": str(rel_path),
            "sha256": hash_file(filepath),
            "size": filepath.stat().st_size
        })
        print(f"  Backed up: {rel_path}")

    manifest_path = backup_root / MANIFEST_FILE
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"\nBackup complete!")
    print(f"  Location: {backup_root}")
    print(f"  Manifest: {manifest_path}")
    print(f"\nTo restore: python tools/backup_game.py \"{install}\" --restore")


def restore_backup(install_path, backup_path=None):
    install = Path(install_path)

    if backup_path:
        backup_root = Path(backup_path)
    else:
        backup_base = Path(BACKUP_DIR)
        backups = sorted(backup_base.glob("fifa16_*"), reverse=True)
        if not backups:
            print("No backups found!")
            sys.exit(1)
        backup_root = backups[0]

    manifest_path = backup_root / MANIFEST_FILE
    if not manifest_path.exists():
        print(f"No manifest found at {manifest_path}")
        sys.exit(1)

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    print(f"Restoring from: {backup_root}")
    print(f"Original install: {manifest['install_path']}")

    for file_info in manifest["files"]:
        rel_path = file_info["original"]
        backup_file = backup_root / rel_path
        original_file = install / rel_path

        if backup_file.exists():
            original_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup_file, original_file)
            print(f"  Restored: {rel_path}")

    print("\nRestore complete!")


def main():
    parser = argparse.ArgumentParser(description="Backup/restore FIFA 16 game files")
    parser.add_argument("install_path", help="Path to FIFA 16 installation")
    parser.add_argument("--restore", action="store_true", help="Restore from backup")
    parser.add_argument("--backup-path", help="Specific backup path to restore from")
    args = parser.parse_args()

    if args.restore:
        restore_backup(args.install_path, args.backup_path)
    else:
        create_backup(args.install_path)


if __name__ == "__main__":
    main()
