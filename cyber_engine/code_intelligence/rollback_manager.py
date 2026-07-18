"""
Chhoti Don EvolveX - Rollback Manager
Advanced backup and rollback system with versioning.
Phase 2.2 - Full Upgrade
"""

import os
import shutil
import time
import datetime
from typing import Dict, List, List


BACKUP_DIR= ".evolveX_backups"
MAX_VERSIONS = 5


def _get_backup_path(file_path: str, version: int = 0) -> str:
    """Backup path calculate karo."""
    if version == 0:
        return file_path + ".bak"
    return file_path + f".bak.v{version}"


def create_backup(file_path: str) -> str:
    """
    File backup create karo.
    Preserved + upgraded with versioning.
    """
    backup_path = _get_backup_path(file_path)

    # Rotate existing backups
    for i in range(MAX_VERSIONS - 1, 0, -1):
        older = _get_backup_path(file_path, i)
        newer = _get_backup_path(file_path, i + 1)
        if os.path.exists(older):
            shutil.copyfile(older, newer)

    # Current .bak → .bak.v1
    if os.path.exists(backup_path):
        shutil.copyfile(backup_path, _get_backup_path(file_path, 1))

    shutil.copyfile(file_path, backup_path)
    return backup_path


def restore_backup(file_path: str, version: int = 0) -> bool:
    """
    Restore file from backup.
    Preserved + upgraded.
    """
    backup_path = _get_backup_path(file_path, version)

    if os.path.exists(backup_path):
        shutil.copyfile(backup_path, file_path)
        if version == 0:
            os.remove(backup_path)
        return True
    return False


def delete_backup(file_path: str) -> None:
    """
    Delete backup file.
    Preserved.
    """
    backup_path = _get_backup_path(file_path)
    if os.path.exists(backup_path):
        os.remove(backup_path)


def list_backups(file_path: str) -> List[Dict]:
    """Available backups list karo."""
    backups = []
    backup_path = _get_backup_path(file_path)

    if os.path.exists(backup_path):
        stat = os.stat(backup_path)
        backups.append({
            "version": 0,
            "path": backup_path,
            "size": stat.st_size,
            "modified": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
        })

    for i in range(1, MAX_VERSIONS + 1):
        vpath = _get_backup_path(file_path, i)
        if os.path.exists(vpath):
            stat = os.stat(vpath)
            backups.append({
                "version": i,
                "path": vpath,
                "size": stat.st_size,
                "modified": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })

    return backups


def cleanup_old_backups(file_path: str, keep_versions: int = 2) -> int:
    """Old backups cleanup karo."""
    cleaned = 0
    for i in range(keep_versions + 1, MAX_VERSIONS + 1):
        vpath = _get_backup_path(file_path, i)
        if os.path.exists(vpath):
            os.remove(vpath)
            cleaned += 1
    return cleaned


def backup_project(project_path: str, backup_name: str = None) -> Dict:
    """Full project backup create karo."""
    if not backup_name:
        backup_name = f"project_backup_{int(time.time())}"

    backup_dir = os.path.join(BACKUP_DIR, backup_name)

    try:
        shutil.copytree(
            project_path,
            backup_dir,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".git", "*.bak*")
        )
        return {
            "status": "success",
            "backup_path": backup_dir,
            "name": backup_name,
            "timestamp": datetime.datetime.utcnow().isoformat(),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
