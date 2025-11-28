"""Backup management for deduplication operations.

This module handles creating, storing, and restoring backups
during deduplication refactoring operations.
"""
import hashlib
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from ...core.logging import get_logger


class DeduplicationBackupManager:
    """Manages backups for deduplication operations."""

    def __init__(self, project_folder: str) -> None:
        """Initialize backup manager.

        Args:
            project_folder: Project root folder
        """
        self.project_folder = project_folder
        self.backup_base_dir = Path(project_folder) / ".ast-grep-backups"
        self.logger = get_logger("deduplication.backup")

    def create_backup(
        self,
        files: List[str],
        metadata: Dict[str, Any]
    ) -> str:
        """Create backup of files before modification.

        Args:
            files: List of file paths to backup
            metadata: Additional metadata to store with backup

        Returns:
            Backup ID for later restoration
        """
        self.logger.info("create_backup_start", file_count=len(files))

        # Generate backup ID with timestamp
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")[:-3]
        backup_id = f"dedup-backup-{timestamp}"
        backup_dir = self.backup_base_dir / backup_id

        # Handle collision by appending counter
        counter = 1
        while backup_dir.exists():
            backup_id = f"dedup-backup-{timestamp}-{counter}"
            backup_dir = self.backup_base_dir / backup_id
            counter += 1

        # Create backup directory
        backup_dir.mkdir(parents=True, exist_ok=True)

        # Compute hashes for all files
        original_hashes: Dict[str, str] = {}
        for file_path in files:
            if os.path.exists(file_path):
                original_hashes[file_path] = self.get_file_hash(file_path)

        # Add original_hashes to metadata
        metadata_with_hashes = {**metadata, "original_hashes": original_hashes}

        # Build backup metadata
        backup_metadata: Dict[str, Any] = {
            "backup_id": backup_id,
            "backup_type": "deduplication",
            "timestamp": datetime.now().isoformat(),
            "project_folder": self.project_folder,
            "files": [],
            "deduplication_metadata": metadata_with_hashes
        }

        # Copy files to backup
        for file_path in files:
            if not os.path.exists(file_path):
                self.logger.warning("file_not_found_for_backup", file=file_path)
                continue

            rel_path = os.path.relpath(file_path, self.project_folder)
            backup_file_path = backup_dir / rel_path

            # Create parent directories
            backup_file_path.parent.mkdir(parents=True, exist_ok=True)

            # Copy file preserving metadata
            shutil.copy2(file_path, backup_file_path)

            backup_metadata["files"].append({
                "original": file_path,
                "relative": rel_path,
                "backup": str(backup_file_path),
                "original_hash": original_hashes.get(file_path, "")
            })

        # Save metadata
        metadata_path = backup_dir / "backup-metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(backup_metadata, f, indent=2)

        self.logger.info(
            "create_backup_complete",
            backup_id=backup_id,
            files_backed_up=len(backup_metadata["files"])
        )

        return backup_id

    def rollback(self, backup_id: str) -> List[str]:
        """Rollback changes using backup.

        Args:
            backup_id: Backup ID to restore from

        Returns:
            List of restored file paths
        """
        self.logger.info("rollback_start", backup_id=backup_id)

        backup_dir = self.backup_base_dir / backup_id
        metadata_path = backup_dir / "backup-metadata.json"

        if not metadata_path.exists():
            raise ValueError(f"Backup '{backup_id}' not found or invalid")

        # Load metadata
        with open(metadata_path, "r") as f:
            metadata = json.load(f)

        restored_files = []

        # Restore each file
        for file_info in metadata.get("files", []):
            original_path = file_info["original"]
            backup_path = file_info["backup"]

            if not os.path.exists(backup_path):
                self.logger.warning(
                    "backup_file_not_found",
                    original=original_path,
                    backup=backup_path
                )
                continue

            try:
                # Restore file
                shutil.copy2(backup_path, original_path)
                restored_files.append(original_path)
                self.logger.debug("file_restored", file=original_path)

            except Exception as e:
                self.logger.error(
                    "restore_failed",
                    file=original_path,
                    error=str(e)
                )

        self.logger.info(
            "rollback_complete",
            backup_id=backup_id,
            files_restored=len(restored_files)
        )

        return restored_files

    def cleanup_old_backups(self, days: int = 30) -> int:
        """Remove backups older than specified days.

        Args:
            days: Number of days to keep backups

        Returns:
            Number of backups removed
        """
        if not self.backup_base_dir.exists():
            return 0

        from datetime import timedelta
        cutoff_date = datetime.now() - timedelta(days=days)
        removed_count = 0

        for backup_dir in self.backup_base_dir.iterdir():
            if not backup_dir.is_dir():
                continue

            metadata_path = backup_dir / "backup-metadata.json"
            if not metadata_path.exists():
                continue

            try:
                with open(metadata_path, "r") as f:
                    metadata = json.load(f)

                timestamp_str = metadata.get("timestamp", "")
                if not timestamp_str:
                    continue

                backup_date = datetime.fromisoformat(timestamp_str)
                if backup_date < cutoff_date:
                    shutil.rmtree(backup_dir)
                    removed_count += 1
                    self.logger.info(
                        "old_backup_removed",
                        backup_id=metadata.get("backup_id"),
                        age_days=(datetime.now() - backup_date).days
                    )

            except Exception as e:
                self.logger.warning(
                    "cleanup_failed",
                    backup_dir=str(backup_dir),
                    error=str(e)
                )

        return removed_count

    def get_file_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of a file's contents.

        Args:
            file_path: Path to file

        Returns:
            SHA-256 hash as hexadecimal string
        """
        try:
            with open(file_path, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except (OSError, IOError) as e:
            self.logger.warning("hash_calculation_failed", file=file_path, error=str(e))
            return ""

    def list_backups(self) -> List[Dict[str, Any]]:
        """List all available backups.

        Returns:
            List of backup metadata dictionaries
        """
        if not self.backup_base_dir.exists():
            return []

        backups = []

        for backup_dir in self.backup_base_dir.iterdir():
            if not backup_dir.is_dir():
                continue

            metadata_path = backup_dir / "backup-metadata.json"
            if not metadata_path.exists():
                continue

            try:
                with open(metadata_path, "r") as f:
                    metadata = json.load(f)
                    backups.append(metadata)
            except Exception as e:
                self.logger.warning(
                    "metadata_read_failed",
                    backup_dir=str(backup_dir),
                    error=str(e)
                )

        # Sort by timestamp (newest first)
        backups.sort(
            key=lambda b: b.get("timestamp", ""),
            reverse=True
        )

        return backups
