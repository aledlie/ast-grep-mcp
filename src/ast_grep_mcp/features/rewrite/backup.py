"""Backup management for code rewrites."""

import hashlib
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ast_grep_mcp.core.logging import get_logger


def create_backup(files_to_backup: List[str], project_folder: str) -> str:
    """Create a timestamped backup of files before rewriting.

    Args:
        files_to_backup: List of absolute file paths to backup
        project_folder: Project root folder

    Returns:
        backup_id: Unique identifier for this backup (timestamp-based)
    """
    logger = get_logger("rewrite.backup")

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")[:-3]
    backup_id = f"backup-{timestamp}"
    backup_base_dir = os.path.join(project_folder, ".ast-grep-backups")
    backup_dir = os.path.join(backup_base_dir, backup_id)

    # Handle collision by appending counter suffix
    counter = 1
    while os.path.exists(backup_dir):
        backup_id = f"backup-{timestamp}-{counter}"
        backup_dir = os.path.join(backup_base_dir, backup_id)
        counter += 1

    os.makedirs(backup_dir, exist_ok=True)

    metadata: Dict[str, Any] = {
        "backup_id": backup_id,
        "timestamp": datetime.now().isoformat(),
        "files": [],
        "project_folder": project_folder
    }

    for file_path in files_to_backup:
        if not os.path.exists(file_path):
            logger.warning("file_not_found_for_backup", file_path=file_path)
            continue

        rel_path = os.path.relpath(file_path, project_folder)
        backup_file_path = os.path.join(backup_dir, rel_path)

        os.makedirs(os.path.dirname(backup_file_path), exist_ok=True)
        shutil.copy2(file_path, backup_file_path)

        metadata["files"].append({
            "original": file_path,
            "relative": rel_path,
            "backup": backup_file_path
        })

    metadata_path = os.path.join(backup_dir, "backup-metadata.json")
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    logger.info(
        "backup_created",
        backup_id=backup_id,
        files_backed_up=len(metadata["files"]),
        backup_dir=backup_dir
    )

    return backup_id


def create_deduplication_backup(
    files_to_backup: List[str],
    project_folder: str,
    duplicate_group_id: int,
    strategy: str,
    original_hashes: Dict[str, str]
) -> str:
    """Create a backup with deduplication-specific metadata.

    Args:
        files_to_backup: List of absolute file paths to backup
        project_folder: Project root folder
        duplicate_group_id: ID of the duplicate group being refactored
        strategy: Deduplication strategy used (e.g., 'extract_function', 'consolidate')
        original_hashes: Dict mapping file paths to their content hashes

    Returns:
        backup_id: Unique identifier for this backup (timestamp-based)
    """
    logger = get_logger("rewrite.backup")

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")[:-3]
    backup_id = f"dedup-backup-{timestamp}"
    backup_base_dir = os.path.join(project_folder, ".ast-grep-backups")
    backup_dir = os.path.join(backup_base_dir, backup_id)

    # Handle collision by appending counter suffix
    counter = 1
    while os.path.exists(backup_dir):
        backup_id = f"dedup-backup-{timestamp}-{counter}"
        backup_dir = os.path.join(backup_base_dir, backup_id)
        counter += 1

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
            "affected_files": files_to_backup
        }
    }

    for file_path in files_to_backup:
        if not os.path.exists(file_path):
            logger.warning("file_not_found_for_backup", file_path=file_path)
            continue

        rel_path = os.path.relpath(file_path, project_folder)
        backup_file_path = os.path.join(backup_dir, rel_path)

        os.makedirs(os.path.dirname(backup_file_path), exist_ok=True)
        shutil.copy2(file_path, backup_file_path)

        metadata["files"].append({
            "original": file_path,
            "relative": rel_path,
            "backup": backup_file_path,
            "original_hash": original_hashes.get(file_path, "")
        })

    metadata_path = os.path.join(backup_dir, "backup-metadata.json")
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    logger.info(
        "deduplication_backup_created",
        backup_id=backup_id,
        files_backed_up=len(metadata["files"]),
        backup_dir=backup_dir,
        duplicate_group_id=duplicate_group_id,
        strategy=strategy
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
        with open(file_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    except (OSError, IOError):
        return ""


def verify_backup_integrity(backup_id: str, project_folder: str) -> Dict[str, Any]:
    """Verify that a backup can be safely restored.

    Args:
        backup_id: The unique identifier of the backup
        project_folder: Project root folder

    Returns:
        Dict with verification results:
        - valid: Whether the backup is valid and restorable
        - errors: List of errors found
        - warnings: List of warnings
        - metadata: The backup metadata if valid
    """
    logger = get_logger("rewrite.backup")

    backup_dir = os.path.join(project_folder, ".ast-grep-backups", backup_id)
    metadata_path = os.path.join(backup_dir, "backup-metadata.json")

    result = {
        "valid": False,
        "errors": [],
        "warnings": [],
        "metadata": None
    }

    # Check backup directory exists
    if not os.path.exists(backup_dir):
        result["errors"].append(f"Backup directory not found: {backup_dir}")
        return result

    # Check metadata file exists
    if not os.path.exists(metadata_path):
        result["errors"].append(f"Backup metadata not found: {metadata_path}")
        return result

    # Load and validate metadata
    try:
        with open(metadata_path, "r") as f:
            metadata = json.load(f)
            result["metadata"] = metadata
    except (json.JSONDecodeError, IOError) as e:
        result["errors"].append(f"Failed to load metadata: {e}")
        return result

    # Verify all backup files exist
    for file_info in metadata.get("files", []):
        backup_path = file_info.get("backup")
        if backup_path and not os.path.exists(backup_path):
            result["errors"].append(f"Backup file missing: {backup_path}")

    # Check for conflicts with current files
    for file_info in metadata.get("files", []):
        original_path = file_info.get("original")
        if original_path and os.path.exists(original_path):
            current_hash = get_file_hash(original_path)
            if "original_hash" in file_info and file_info["original_hash"] != current_hash:
                result["warnings"].append(
                    f"File has been modified since backup: {original_path}"
                )

    result["valid"] = len(result["errors"]) == 0

    logger.info(
        "backup_integrity_verified",
        backup_id=backup_id,
        valid=result["valid"],
        error_count=len(result["errors"]),
        warning_count=len(result["warnings"])
    )

    return result


def restore_backup(backup_id: str, project_folder: str) -> Dict[str, Any]:
    """Restore files from a backup.

    Args:
        backup_id: The unique identifier of the backup to restore
        project_folder: Project root folder

    Returns:
        Dict with restoration results:
        - success: Whether restoration was successful
        - restored_files: List of restored file paths
        - errors: List of errors encountered
    """
    logger = get_logger("rewrite.backup")

    # First verify backup integrity
    verification = verify_backup_integrity(backup_id, project_folder)

    result = {
        "success": False,
        "restored_files": [],
        "errors": []
    }

    if not verification["valid"]:
        result["errors"].extend(verification["errors"])
        return result

    metadata = verification["metadata"]

    # Restore each file
    for file_info in metadata.get("files", []):
        backup_path = file_info.get("backup")
        original_path = file_info.get("original")

        if not backup_path or not original_path:
            result["errors"].append(f"Invalid file info in metadata: {file_info}")
            continue

        try:
            # Create parent directory if needed
            os.makedirs(os.path.dirname(original_path), exist_ok=True)

            # Copy backup file to original location
            shutil.copy2(backup_path, original_path)
            result["restored_files"].append(original_path)

        except Exception as e:
            result["errors"].append(f"Failed to restore {original_path}: {e}")

    result["success"] = len(result["errors"]) == 0

    logger.info(
        "backup_restored",
        backup_id=backup_id,
        success=result["success"],
        restored_count=len(result["restored_files"]),
        error_count=len(result["errors"])
    )

    return result


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

        metadata_path = os.path.join(backup_dir, "backup-metadata.json")

        # Skip if no metadata
        if not os.path.exists(metadata_path):
            continue

        try:
            with open(metadata_path, "r") as f:
                metadata = json.load(f)

            # Calculate backup size
            backup_size = sum(
                os.path.getsize(os.path.join(backup_dir, root, file))
                for root, _, files in os.walk(backup_dir)
                for file in files
            )

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
                backup_info["deduplication_info"] = {
                    "duplicate_group_id": metadata["deduplication_metadata"].get("duplicate_group_id"),
                    "strategy": metadata["deduplication_metadata"].get("strategy")
                }

            backups.append(backup_info)

        except (json.JSONDecodeError, IOError) as e:
            logger.warning(
                "failed_to_load_backup_metadata",
                backup_name=backup_name,
                error=str(e)
            )
            continue

    # Sort by timestamp (newest first)
    backups.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

    logger.info(
        "listed_backups",
        backup_count=len(backups),
        project_folder=project_folder
    )

    return backups