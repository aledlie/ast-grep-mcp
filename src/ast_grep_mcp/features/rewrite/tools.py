"""Rewrite feature MCP tool definitions."""

from typing import Any, Dict, List

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from ast_grep_mcp.features.rewrite.service import (
    list_backups_impl,
    rewrite_code_impl,
    rollback_rewrite_impl,
)


def register_rewrite_tools(mcp: FastMCP) -> None:
    """Register rewrite-related MCP tools.

    Args:
        mcp: FastMCP instance to register tools with
    """

    @mcp.tool()
    def rewrite_code(
        project_folder: str = Field(description="The absolute path to the project folder"),
        yaml_rule: str = Field(description="YAML rule with 'fix' field for code transformation"),
        dry_run: bool = Field(
            default=True,
            description="Preview changes without applying (default: true for safety)"
        ),
        backup: bool = Field(
            default=True,
            description="Create backup before applying changes (default: true)"
        ),
        max_file_size_mb: int = Field(
            default=0,
            description="Skip files larger than this (0 = unlimited)"
        ),
        workers: int = Field(
            default=0,
            description="Number of worker threads (0 = auto)"
        )
    ) -> Dict[str, Any]:
        """
        Rewrite code using ast-grep fix rules. Apply automated code transformations safely.

        SAFETY FEATURES:
        - dry_run=True by default (preview before applying)
        - Automatic backups before changes
        - Returns diff preview or list of modified files

        Example YAML Rule:
        ```yaml
        id: replace-var-with-const
        language: javascript
        rule:
          pattern: var $NAME = $VAL
        fix: const $NAME = $VAL
        ```

        Returns:
        - dry_run=True: Preview with diffs showing proposed changes
        - dry_run=False: backup_id and list of modified files
        """
        return rewrite_code_impl(
            project_folder,
            yaml_rule,
            dry_run,
            backup,
            max_file_size_mb,
            workers
        )

    @mcp.tool()
    def rollback_rewrite(
        backup_id: str = Field(
            description="The backup ID from a previous rewrite operation"
        ),
        project_folder: str = Field(
            description="The absolute path to the project folder"
        )
    ) -> Dict[str, Any]:
        """
        Restore files from a backup created during rewrite operations.

        Use this to undo changes from rewrite_code when:
        - Syntax validation fails
        - Changes had unintended effects
        - You need to restore previous state

        Get available backup_ids using list_backups().

        Returns:
        - success: Whether restoration was successful
        - restored_files: List of restored file paths
        - errors: Any errors encountered (if restoration failed)
        """
        return rollback_rewrite_impl(backup_id, project_folder)

    @mcp.tool()
    def list_backups(
        project_folder: str = Field(
            description="The absolute path to the project folder"
        )
    ) -> List[Dict[str, Any]]:
        """
        List all available backups in the project.

        Shows backups created by rewrite_code and apply_deduplication operations.
        Backups are stored in .ast-grep-backups/ directory.

        Returns list of backups with:
        - backup_id: Unique identifier (use with rollback_rewrite)
        - timestamp: When backup was created
        - file_count: Number of files in backup
        - size_bytes: Total backup size
        - backup_type: 'standard' or 'deduplication'
        """
        return list_backups_impl(project_folder)
