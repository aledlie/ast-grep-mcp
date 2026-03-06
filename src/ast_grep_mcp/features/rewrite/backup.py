"""Backup management for code rewrites."""

import hashlib
import json
import os
import shutil
from datetime import datetime
from typing import Any, Dict, List, Optional

from ast_grep_mcp.constants import FormattingDefaults
from ast_grep_mcp.core.logging import get_logger


def _resolve_backup_dir(prefix: str, timestamp: str, backup_base_dir: str) -> tuple[str, str]:
    backup_id = f"{prefix}-{timestamp}"
    backup_dir = os.path.join(backup_base_dir, backup_id)
    counter = 1
    while os.path.exists(backup_dir):
        backup_id = f"{prefix}-{timestamp}-{counter}"
        backup_dir = os.path.join(backup_base_dir, backup_id)
        counter += 1
    return backup_id, backup_dir


def _copy_file_to_backup(
    file_path: str, project_folder: str, backup_dir: str, logger: Any, original_hashes: Optional[Dict[str, str]] = None
) -> Optional[Dict[str, Any]]:
    if not os.path.exists(file_path):
        logger.warning("file_not_found_for_backup", file_path=file_path)
        return None
    rel_path = os.path.relpath(file_path, project_folder)
    backup_file_path = os.path.join(backup_dir, rel_path)
    os.makedirs(os.path.dirname(backup_file_path), exist_ok=True)
    shutil.copy2(file_path, backup_file_path)
    entry: Dict[str, Any] = {"original": file_path, "relative": rel_path, "backup": backup_file_path}
    if original_hashes is not None:
        entry["original_hash"] = original_hashes.get(file_path, "")
    return entry


def create_backup(files_to_backup: List[str], project_folder: str) -> str:
    logger = get_logger("rewrite.backup")
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")[:-FormattingDefaults.TIMESTAMP_MS_TRIM]
    backup_base_dir = os.path.join(project_folder, ".ast-grep-backups")
    backup_id, backup_dir = _resolve_backup_dir("backup", timestamp, backup_base_dir)
    os.makedirs(backup_dir, exist_ok=True)

    metadata: Dict[str, Any] = {
        "backup_id": backup_id,
        "timestamp": datetime.now().isoformat(),
        "files": [],
        "project_folder": project_folder,
    }
    for file_path in files_to_backup:
        entry = _copy_file_to_backup(file_path, project_folder, backup_dir, logger)
        if entry:
            metadata["files"].append(entry)

    with open(os.path.join(backup_dir, "backup-metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)

    logger.info("backup_created", backup_id=backup_id, files_backed_up=len(metadata["files"]), backup_dir=backup_dir)
    return backup_id


def create_deduplication_backup(
    files_to_backup: List[str], project_folder: str, duplicate_group_id: int, strategy: str, original_hashes: Dict[str, str]
) -> str:
    logger = get_logger("rewrite.backup")
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")[:-FormattingDefaults.TIMESTAMP_MS_TRIM]
    backup_base_dir = os.path.join(project_folder, ".ast-grep-backups")
    backup_id, backup_dir = _resolve_backup_dir("dedup-backup", timestamp, backup_base_dir)
    os.makedirs(backup_dir, exist_ok=True)

    metadata: Dict[str, Any] = {
        "backup_id": backup_id,
        "backup_type": "deduplication",
        "timestamp": datetime.now().isoformat(),
        "files": [],
        "project_folder": project_folder,
        "deduplication_metadata": {
            "duplicate_group_id": duplicate_group_id,
            "strategy": strategy,
            "original_hashes": original_hashes,
            "affected_files": files_to_backup,
        },
    }
    for file_path in files_to_backup:
        entry = _copy_file_to_backup(file_path, project_folder, backup_dir, logger, original_hashes)
        if entry:
            metadata["files"].append(entry)

    with open(os.path.join(backup_dir, "backup-metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)

    logger.info(
        "deduplication_backup_created",
        backup_id=backup_id,
        files_backed_up=len(metadata["files"]),
        backup_dir=backup_dir,
        duplicate_group_id=duplicate_group_id,
        strategy=strategy,
    )
    return backup_id


def get_file_hash(file_path: str) -> str:
    """Calculate SHA-256 hash of a file's contents.

    Args:
        file_path: Absolute path to the file

    Returns:
        Hex digest of the file's SHA-256 hash
    """
    try:
        with open(file_path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except (OSError, IOError):
        return ""


def _verify_backup_files_exist(metadata: Dict[str, Any], errors: List[str]) -> None:
    for file_info in metadata.get("files", []):
        backup_path = file_info.get("backup")
        if backup_path and not os.path.exists(backup_path):
            errors.append(f"Backup file missing: {backup_path}")


def _check_file_conflicts(metadata: Dict[str, Any], warnings: List[str]) -> None:
    for file_info in metadata.get("files", []):
        original_path = file_info.get("original")
        if original_path and os.path.exists(original_path):
            current_hash = get_file_hash(original_path)
            if "original_hash" in file_info and file_info["original_hash"] != current_hash:
                warnings.append(f"File has been modified since backup: {original_path}")


def _load_integrity_metadata(backup_dir: str, metadata_path: str, result: Dict[str, Any]) -> bool:
    if not os.path.exists(backup_dir):
        result["errors"].append(f"Backup directory not found: {backup_dir}")
        return False
    if not os.path.exists(metadata_path):
        result["errors"].append(f"Backup metadata not found: {metadata_path}")
        return False
    try:
        with open(metadata_path, "r") as f:
            result["metadata"] = json.load(f)
        return True
    except (json.JSONDecodeError, IOError) as e:
        result["errors"].append(f"Failed to load metadata: {e}")
        return False


def verify_backup_integrity(backup_id: str, project_folder: str) -> Dict[str, Any]:
    logger = get_logger("rewrite.backup")
    backup_dir = os.path.join(project_folder, ".ast-grep-backups", backup_id)
    metadata_path = os.path.join(backup_dir, "backup-metadata.json")
    result: Dict[str, Any] = {"valid": False, "errors": [], "warnings": [], "metadata": None}

    if not _load_integrity_metadata(backup_dir, metadata_path, result):
        return result

    _verify_backup_files_exist(result["metadata"], result["errors"])
    _check_file_conflicts(result["metadata"], result["warnings"])
    result["valid"] = len(result["errors"]) == 0

    logger.info(
        "backup_integrity_verified",
        backup_id=backup_id,
        valid=result["valid"],
        error_count=len(result["errors"]),
        warning_count=len(result["warnings"]),
    )
    return result


def _restore_single_file(file_info: Dict[str, Any], result: Dict[str, Any]) -> None:
    backup_path = file_info.get("backup")
    original_path = file_info.get("original")
    if not backup_path or not original_path:
        result["errors"].append(f"Invalid file info in metadata: {file_info}")
        return
    try:
        os.makedirs(os.path.dirname(original_path), exist_ok=True)
        shutil.copy2(backup_path, original_path)
        result["restored_files"].append(original_path)
    except Exception as e:
        result["errors"].append(f"Failed to restore {original_path}: {e}")


def restore_backup(backup_id: str, project_folder: str) -> Dict[str, Any]:
    logger = get_logger("rewrite.backup")
    verification = verify_backup_integrity(backup_id, project_folder)
    result: Dict[str, Any] = {"success": False, "restored_files": [], "errors": []}

    if not verification["valid"]:
        result["errors"].extend(verification["errors"])
        return result

    for file_info in verification["metadata"].get("files", []):
        _restore_single_file(file_info, result)

    result["success"] = len(result["errors"]) == 0
    logger.info(
        "backup_restored",
        backup_id=backup_id,
        success=result["success"],
        restored_count=len(result["restored_files"]),
        error_count=len(result["errors"]),
    )
    return result


def _calculate_backup_size(backup_dir: str) -> int:
    """Calculate total size of all files in backup directory.

    Args:
        backup_dir: Path to backup directory

    Returns:
        Total size in bytes
    """
    return sum(os.path.getsize(os.path.join(backup_dir, root, file)) for root, _, files in os.walk(backup_dir) for file in files)


def _build_backup_info(metadata: Dict[str, Any], backup_name: str, backup_size: int) -> Dict[str, Any]:
    """Build backup information dictionary from metadata.

    Args:
        metadata: Backup metadata loaded from JSON
        backup_name: Name of the backup directory
        backup_size: Total size of backup in bytes

    Returns:
        Formatted backup information dictionary
    """
    backup_info = {
        "backup_id": metadata.get("backup_id", backup_name),
        "timestamp": metadata.get("timestamp"),
        "backup_type": metadata.get("backup_type", "standard"),
        "file_count": len(metadata.get("files", [])),
        "size_bytes": backup_size,
        "project_folder": metadata.get("project_folder"),
    }

    # Add deduplication info if present
    if "deduplication_metadata" in metadata:
        dedup_meta = metadata["deduplication_metadata"]
        backup_info["deduplication_info"] = {
            "duplicate_group_id": dedup_meta.get("duplicate_group_id"),
            "strategy": dedup_meta.get("strategy"),
        }

    return backup_info


def _load_backup_info(backup_dir: str, backup_name: str, logger: Any) -> Optional[Dict[str, Any]]:
    """Load and parse backup information from a backup directory.

    Args:
        backup_dir: Full path to backup directory
        backup_name: Name of the backup
        logger: Logger instance

    Returns:
        Backup info dict or None if invalid
    """
    metadata_path = os.path.join(backup_dir, "backup-metadata.json")

    # Skip if no metadata
    if not os.path.exists(metadata_path):
        return None

    try:
        with open(metadata_path, "r") as f:
            metadata = json.load(f)

        backup_size = _calculate_backup_size(backup_dir)
        return _build_backup_info(metadata, backup_name, backup_size)

    except (json.JSONDecodeError, IOError) as e:
        logger.warning("failed_to_load_backup_metadata", backup_name=backup_name, error=str(e))
        return None


def list_available_backups(project_folder: str) -> List[Dict[str, Any]]:
    """List all available backups in the project.

    Args:
        project_folder: Project root folder

    Returns:
        List of backup information dictionaries
    """
    logger = get_logger("rewrite.backup")
    backup_base_dir = os.path.join(project_folder, ".ast-grep-backups")

    if not os.path.exists(backup_base_dir):
        return []

    backups = []

    for backup_name in os.listdir(backup_base_dir):
        backup_dir = os.path.join(backup_base_dir, backup_name)

        # Skip if not a directory
        if not os.path.isdir(backup_dir):
            continue

        backup_info = _load_backup_info(backup_dir, backup_name, logger)
        if backup_info:
            backups.append(backup_info)

    # Sort by timestamp (newest first)
    backups.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

    logger.info("listed_backups", backup_count=len(backups), project_folder=project_folder)

    return backups
