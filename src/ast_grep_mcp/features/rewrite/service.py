"""Rewrite feature service - implements code transformation functionality."""

import json
import os
import subprocess
import tempfile
import time
from typing import Any, Dict, List, Optional

import sentry_sdk
import yaml

from ast_grep_mcp.core.exceptions import InvalidYAMLError
from ast_grep_mcp.core.executor import (
    filter_files_by_size,
    run_ast_grep,
    stream_ast_grep_results,
)
from ast_grep_mcp.core.logging import get_logger
from ast_grep_mcp.features.rewrite.backup import (
    create_backup,
    list_available_backups,
    restore_backup,
)


def validate_syntax(file_path: str, language: str) -> Dict[str, Any]:
    """Validate syntax of a rewritten file.

    Args:
        file_path: Absolute path to the file to validate
        language: Programming language (python, javascript, typescript, etc.)

    Returns:
        Dict with 'valid' (bool), 'error' (str if invalid), 'language' (str)
    """
    result: Dict[str, Any] = {
        "file": file_path,
        "language": language,
        "valid": True,
        "error": None
    }

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Python syntax validation
        if language == "python":
            try:
                compile(content, file_path, 'exec')
            except SyntaxError as e:
                result["valid"] = False
                result["error"] = f"Line {e.lineno}: {e.msg}"
                return result

        # JavaScript/TypeScript validation (using external validator if available)
        elif language in ["javascript", "typescript", "tsx", "jsx"]:
            # Try using node if available
            try:
                node_code = f"""
try {{
    new Function({json.dumps(content)});
    console.log("VALID");
}} catch(e) {{
    console.log("INVALID: " + e.message);
}}
"""
                node_result = subprocess.run(
                    ["node", "-e", node_code],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if "INVALID:" in node_result.stdout:
                    result["valid"] = False
                    result["error"] = node_result.stdout.replace("INVALID: ", "").strip()
            except (subprocess.SubprocessError, FileNotFoundError):
                # Node not available, skip validation
                result["valid"] = True
                result["error"] = "JavaScript validation skipped (node not available)"

        # Java validation
        elif language == "java":
            # Basic Java syntax check using javac if available
            try:
                javac_result = subprocess.run(
                    ["javac", "-Xlint:none", file_path],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if javac_result.returncode != 0:
                    result["valid"] = False
                    result["error"] = javac_result.stderr[:500]  # Limit error message
                # Clean up .class file if compilation succeeded
                else:
                    class_file = file_path.replace('.java', '.class')
                    if os.path.exists(class_file):
                        os.remove(class_file)
            except (subprocess.SubprocessError, FileNotFoundError):
                result["valid"] = True
                result["error"] = "Java validation skipped (javac not available)"

        # For other languages, basic checks only
        else:
            result["valid"] = True
            result["error"] = f"Syntax validation not supported for {language}"

    except Exception as e:
        result["valid"] = False
        result["error"] = f"Validation error: {str(e)}"

    return result


def validate_rewrites(modified_files: List[str], language: str) -> Dict[str, Any]:
    """Validate syntax of all rewritten files.

    Args:
        modified_files: List of file paths that were modified
        language: Programming language

    Returns:
        Dict with validation summary and results per file
    """
    validation_results = []
    failed_count = 0
    skipped_count = 0

    for file_path in modified_files:
        result = validate_syntax(file_path, language)
        validation_results.append(result)

        if not result["valid"]:
            if result["error"] and "not supported" in result["error"]:
                skipped_count += 1
            elif result["error"] and "skipped" in result["error"]:
                skipped_count += 1
            else:
                failed_count += 1

    return {
        "validated": len(modified_files),
        "passed": len(modified_files) - failed_count - skipped_count,
        "failed": failed_count,
        "skipped": skipped_count,
        "results": validation_results
    }


def rewrite_code_impl(
    project_folder: str,
    yaml_rule: str,
    dry_run: bool = True,
    backup: bool = True,
    max_file_size_mb: int = 0,
    workers: int = 0
) -> Dict[str, Any]:
    """
    Implementation of rewrite_code.

    Rewrite code using ast-grep fix rules. Apply automated code transformations safely.

    Args:
        project_folder: The absolute path to the project folder
        yaml_rule: YAML rule with 'fix' field for code transformation
        dry_run: Preview changes without applying (default: true for safety)
        backup: Create backup before applying changes (default: true)
        max_file_size_mb: Skip files larger than this (0 = unlimited)
        workers: Number of worker threads (0 = auto)

    Returns:
        Dict with rewrite results

    Raises:
        InvalidYAMLError: If YAML is invalid
        ValueError: If rule is missing required fields
    """
    logger = get_logger("rewrite.rewrite_code")
    start_time = time.time()

    logger.info(
        "rewrite_code_started",
        project_folder=project_folder,
        dry_run=dry_run,
        backup=backup,
        workers=workers
    )

    try:
        # Validate YAML rule
        try:
            rule_data = yaml.safe_load(yaml_rule)
        except yaml.YAMLError as e:
            raise InvalidYAMLError(f"Invalid YAML rule: {e}", yaml_rule) from e

        if not isinstance(rule_data, dict):
            raise InvalidYAMLError("Rule must be a YAML dictionary", yaml_rule)

        if "fix" not in rule_data:
            raise ValueError("Rule must include a 'fix' field for code rewriting")

        if "language" not in rule_data:
            raise ValueError("Rule must include a 'language' field")

        # Write rule to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(yaml_rule)
            rule_file = f.name

        try:
            # Build command args
            args = ["--rule", rule_file]
            if max_file_size_mb > 0:
                files_to_search, _ = filter_files_by_size(
                    project_folder,
                    max_size_mb=max_file_size_mb,
                    language=rule_data.get("language")
                )
                if files_to_search:
                    search_targets = files_to_search
                else:
                    return {"message": "No files to rewrite (all exceeded size limit)", "changes": []}
            else:
                search_targets = [project_folder]

            if workers > 0:
                args.extend(["--threads", str(workers)])

            args.extend(["--json=stream"] + search_targets)

            # DRY RUN MODE: Preview changes
            if dry_run:
                matches = list(stream_ast_grep_results("scan", args, max_results=0))

                if not matches:
                    execution_time = time.time() - start_time
                    logger.info(
                        "rewrite_code_completed",
                        execution_time_seconds=round(execution_time, 3),
                        dry_run=True,
                        changes_found=0,
                        status="success"
                    )
                    return {
                        "dry_run": True,
                        "message": "No matches found - no changes would be applied",
                        "changes": []
                    }

                # Format changes for preview
                changes = []
                for match in matches:
                    if "replacement" in match:
                        changes.append({
                            "file": match.get("file", "unknown"),
                            "line": match.get("range", {}).get("start", {}).get("line", 0),
                            "original": match.get("text", ""),
                            "replacement": match["replacement"],
                            "rule_id": match.get("ruleId", "unknown")
                        })

                execution_time = time.time() - start_time
                logger.info(
                    "rewrite_code_completed",
                    execution_time_seconds=round(execution_time, 3),
                    dry_run=True,
                    changes_found=len(changes),
                    status="success"
                )

                return {
                    "dry_run": True,
                    "message": f"Found {len(changes)} change(s) - set dry_run=false to apply",
                    "changes": changes
                }

            # ACTUAL REWRITE MODE: Apply changes
            else:
                # Get list of files that will be modified (before rewrite)
                preview_matches = list(stream_ast_grep_results("scan", args, max_results=0))
                files_to_modify = list(set(m.get("file") for m in preview_matches if m.get("file")))

                if not files_to_modify:
                    return {
                        "dry_run": False,
                        "message": "No changes applied - no matches found",
                        "modified_files": [],
                        "backup_id": None
                    }

                # Create backup if requested
                backup_id: Optional[str] = None
                if backup:
                    backup_id = create_backup(files_to_modify, project_folder)
                    logger.info("backup_created", backup_id=backup_id, file_count=len(files_to_modify))

                # Apply rewrite with --update-all
                rewrite_args = ["--rule", rule_file, "--update-all"] + search_targets
                if workers > 0:
                    rewrite_args.insert(0, "--threads")
                    rewrite_args.insert(1, str(workers))

                result = run_ast_grep("scan", rewrite_args)

                # Validate syntax of rewritten files
                language = rule_data.get("language", "unknown")
                validation_summary = validate_rewrites(files_to_modify, language)

                logger.info(
                    "syntax_validation",
                    validated=validation_summary["validated"],
                    passed=validation_summary["passed"],
                    failed=validation_summary["failed"],
                    skipped=validation_summary["skipped"]
                )

                execution_time = time.time() - start_time
                logger.info(
                    "rewrite_code_completed",
                    execution_time_seconds=round(execution_time, 3),
                    dry_run=False,
                    modified_files=len(files_to_modify),
                    backup_id=backup_id,
                    validation_failed=validation_summary["failed"],
                    status="success"
                )

                response = {
                    "dry_run": False,
                    "message": f"Applied changes to {len(files_to_modify)} file(s)",
                    "modified_files": files_to_modify,
                    "backup_id": backup_id,
                    "output": result.stdout,
                    "validation": validation_summary
                }

                # Add warning if validation failed
                if validation_summary["failed"] > 0:
                    response["warning"] = (
                        f"{validation_summary['failed']} file(s) failed syntax validation. "
                        f"Use rollback_rewrite(backup_id='{backup_id}') to restore if needed."
                    )

                return response

        finally:
            # Clean up temporary rule file
            if 'rule_file' in locals() and os.path.exists(rule_file):
                os.unlink(rule_file)

    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(
            "rewrite_code_failed",
            execution_time_seconds=round(execution_time, 3),
            error=str(e)[:200],
            status="failed"
        )
        sentry_sdk.capture_exception(e, extras={
            "function": "rewrite_code_impl",
            "project_folder": project_folder,
            "dry_run": dry_run,
            "execution_time_seconds": round(execution_time, 3)
        })
        raise


def rollback_rewrite_impl(
    backup_id: str,
    project_folder: str
) -> Dict[str, Any]:
    """
    Implementation of rollback_rewrite.

    Restore files from a backup created during rewrite operations.

    Args:
        backup_id: The unique identifier of the backup to restore
        project_folder: The absolute path to the project folder

    Returns:
        Dict with rollback results
    """
    logger = get_logger("rewrite.rollback")
    start_time = time.time()

    logger.info(
        "rollback_started",
        backup_id=backup_id,
        project_folder=project_folder
    )

    try:
        result = restore_backup(backup_id, project_folder)

        execution_time = time.time() - start_time
        logger.info(
            "rollback_completed",
            execution_time_seconds=round(execution_time, 3),
            success=result["success"],
            restored_files=len(result["restored_files"]),
            status="success" if result["success"] else "partial"
        )

        if result["success"]:
            return {
                "success": True,
                "message": f"Successfully restored {len(result['restored_files'])} file(s)",
                "restored_files": result["restored_files"]
            }
        else:
            return {
                "success": False,
                "message": "Rollback encountered errors",
                "restored_files": result["restored_files"],
                "errors": result["errors"]
            }

    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(
            "rollback_failed",
            execution_time_seconds=round(execution_time, 3),
            error=str(e)[:200],
            status="failed"
        )
        sentry_sdk.capture_exception(e, extras={
            "function": "rollback_rewrite_impl",
            "backup_id": backup_id,
            "project_folder": project_folder,
            "execution_time_seconds": round(execution_time, 3)
        })
        raise


def list_backups_impl(project_folder: str) -> List[Dict[str, Any]]:
    """
    Implementation of list_backups.

    List all available backups in the project.

    Args:
        project_folder: The absolute path to the project folder

    Returns:
        List of backup information dictionaries
    """
    logger = get_logger("rewrite.list_backups")

    logger.info(
        "list_backups_started",
        project_folder=project_folder
    )

    try:
        backups = list_available_backups(project_folder)

        logger.info(
            "list_backups_completed",
            backup_count=len(backups)
        )

        return backups

    except Exception as e:
        logger.error(
            "list_backups_failed",
            error=str(e)[:200]
        )
        sentry_sdk.capture_exception(e, extras={
            "function": "list_backups_impl",
            "project_folder": project_folder
        })
        raise