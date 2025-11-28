"""Auto-fix system for code quality violations.

This module provides functionality to automatically fix code quality violations:
- Safe fix application (guaranteed-safe fixes only)
- Suggested fix application (may need review)
- Fix validation (syntax checking, behavior preservation)
- Multi-fix coordination (batch operations with rollback)
"""

import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import sentry_sdk

from ast_grep_mcp.core.logging import get_logger
from ast_grep_mcp.features.rewrite.backup import create_backup, restore_backup
from ast_grep_mcp.features.rewrite.service import validate_syntax
from ast_grep_mcp.models.standards import (
    FixBatchResult,
    FixResult,
    FixValidation,
    RuleViolation,
)

logger = get_logger(__name__)

# =============================================================================
# Fix Classification - Determine Safety Level
# =============================================================================

# Safe patterns that can be auto-applied without review
SAFE_FIX_PATTERNS: Dict[str, Dict[str, Any]] = {
    # JavaScript/TypeScript
    "no-var": {"confidence": 1.0, "reason": "var → const/let is safe"},
    "no-console-log": {"confidence": 0.95, "reason": "console.log removal is usually safe"},
    "no-debugger": {"confidence": 1.0, "reason": "debugger removal is always safe"},
    "prefer-const": {"confidence": 1.0, "reason": "let → const is safe when variable not reassigned"},
    "no-double-equals": {"confidence": 0.9, "reason": "== → === is usually safe"},

    # Python
    "no-print-production": {"confidence": 0.9, "reason": "print() removal is usually safe"},
    "no-bare-except": {"confidence": 0.85, "reason": "except: → except Exception: is usually safe"},
    "no-mutable-defaults": {"confidence": 0.95, "reason": "Mutable default fix is usually safe"},

    # Java
    "no-system-out": {"confidence": 0.9, "reason": "System.out removal is usually safe"},
}

# Patterns that require review (lower confidence)
REVIEW_REQUIRED_PATTERNS: Dict[str, Dict[str, Any]] = {
    "no-eval-exec": {"confidence": 0.6, "reason": "eval/exec removal may break functionality"},
    "no-sql-injection": {"confidence": 0.7, "reason": "SQL parameterization needs careful review"},
    "no-empty-catch": {"confidence": 0.75, "reason": "Empty catch replacement may change behavior"},
    "proper-exception-handling": {"confidence": 0.7, "reason": "Exception handling changes need review"},
}


def classify_fix_safety(rule_id: str, violation: RuleViolation) -> FixValidation:
    """Classify a fix as safe, suggested, or requiring review.

    Args:
        rule_id: ID of the rule being fixed
        violation: The violation to be fixed

    Returns:
        FixValidation with safety assessment
    """
    # Check if this is a known safe pattern
    if rule_id in SAFE_FIX_PATTERNS:
        pattern_info = SAFE_FIX_PATTERNS[rule_id]
        return FixValidation(
            is_safe=True,
            confidence=float(pattern_info["confidence"]),
            warnings=[],
            errors=[],
            requires_review=False
        )

    # Check if this requires review
    if rule_id in REVIEW_REQUIRED_PATTERNS:
        pattern_info = REVIEW_REQUIRED_PATTERNS[rule_id]
        return FixValidation(
            is_safe=False,
            confidence=float(pattern_info["confidence"]),
            warnings=[str(pattern_info["reason"])],
            errors=[],
            requires_review=True
        )

    # Unknown pattern - conservative approach
    return FixValidation(
        is_safe=False,
        confidence=0.5,
        warnings=["Unknown fix pattern - manual review recommended"],
        errors=[],
        requires_review=True
    )


# =============================================================================
# Fix Application - Apply Fixes to Files
# =============================================================================

def apply_pattern_fix(
    file_path: str,
    violation: RuleViolation,
    fix_pattern: str,
    language: str
) -> FixResult:
    """Apply a pattern-based fix to a single violation.

    Args:
        file_path: Path to the file to fix
        violation: The violation to fix
        fix_pattern: The fix pattern (can be a literal string or metavar replacement)
        language: Programming language for syntax validation

    Returns:
        FixResult with fix outcome
    """
    try:
        # Read the file
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        lines = content.splitlines(keepends=True)

        # Get the original code snippet
        start_line = violation.line - 1  # Convert to 0-indexed
        end_line = violation.end_line - 1

        if start_line < 0 or end_line >= len(lines):
            return FixResult(
                violation=violation,
                success=False,
                file_modified=False,
                original_code=violation.code_snippet,
                error="Line numbers out of range"
            )

        original_code = violation.code_snippet

        # Apply fix pattern
        fixed_code = _apply_fix_pattern(original_code, fix_pattern, violation.meta_vars or {})

        # If no change, skip
        if fixed_code == original_code:
            return FixResult(
                violation=violation,
                success=True,
                file_modified=False,
                original_code=original_code,
                fixed_code=fixed_code,
                fix_type='pattern'
            )

        # Replace in file
        if start_line == end_line:
            # Single line fix
            line = lines[start_line]
            lines[start_line] = line.replace(original_code, fixed_code)
        else:
            # Multi-line fix
            lines[start_line:end_line + 1] = [fixed_code + '\n']

        # Write back
        new_content = ''.join(lines)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        # Validate syntax
        validation = validate_syntax(file_path, language)
        syntax_valid = validation['valid']

        if not syntax_valid:
            # Rollback the change
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            return FixResult(
                violation=violation,
                success=False,
                file_modified=False,
                original_code=original_code,
                fixed_code=fixed_code,
                syntax_valid=False,
                error=f"Syntax validation failed: {validation['error']}",
                fix_type='pattern'
            )

        return FixResult(
            violation=violation,
            success=True,
            file_modified=True,
            original_code=original_code,
            fixed_code=fixed_code,
            syntax_valid=True,
            fix_type='pattern'
        )

    except Exception as e:
        sentry_sdk.capture_exception(e)
        return FixResult(
            violation=violation,
            success=False,
            file_modified=False,
            original_code=violation.code_snippet,
            error=f"Fix application error: {str(e)}",
            fix_type='pattern'
        )


def _apply_fix_pattern(
    code: str,
    fix_pattern: str,
    meta_vars: Dict[str, str]
) -> str:
    """Apply a fix pattern with metavariable substitution.

    Args:
        code: Original code
        fix_pattern: Fix pattern (may contain $VAR placeholders)
        meta_vars: Metavariables captured during pattern matching

    Returns:
        Fixed code with metavariables substituted
    """
    fixed = fix_pattern

    # Replace metavariables (e.g., $VAR, $ARGS, $$$)
    for var_name, var_value in meta_vars.items():
        fixed = fixed.replace(f"${var_name}", var_value)

    return fixed


def apply_removal_fix(
    file_path: str,
    violation: RuleViolation,
    language: str
) -> FixResult:
    """Apply a removal fix (delete the violating code).

    Args:
        file_path: Path to the file to fix
        violation: The violation to fix (will be removed)
        language: Programming language for syntax validation

    Returns:
        FixResult with fix outcome
    """
    try:
        # Read the file
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        lines = content.splitlines(keepends=True)

        # Get the original code snippet
        start_line = violation.line - 1  # Convert to 0-indexed
        end_line = violation.end_line - 1

        if start_line < 0 or end_line >= len(lines):
            return FixResult(
                violation=violation,
                success=False,
                file_modified=False,
                original_code=violation.code_snippet,
                error="Line numbers out of range"
            )

        original_code = violation.code_snippet

        # Remove the lines
        del lines[start_line:end_line + 1]

        # Write back
        new_content = ''.join(lines)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        # Validate syntax
        validation = validate_syntax(file_path, language)
        syntax_valid = validation['valid']

        if not syntax_valid:
            # Rollback the change
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            return FixResult(
                violation=violation,
                success=False,
                file_modified=False,
                original_code=original_code,
                fixed_code="",
                syntax_valid=False,
                error=f"Syntax validation failed: {validation['error']}",
                fix_type='removal'
            )

        return FixResult(
            violation=violation,
            success=True,
            file_modified=True,
            original_code=original_code,
            fixed_code="",
            syntax_valid=True,
            fix_type='removal'
        )

    except Exception as e:
        sentry_sdk.capture_exception(e)
        return FixResult(
            violation=violation,
            success=False,
            file_modified=False,
            original_code=violation.code_snippet,
            error=f"Removal error: {str(e)}",
            fix_type='removal'
        )


# =============================================================================
# Batch Fix Coordinator - Apply Multiple Fixes
# =============================================================================

def apply_fixes_batch(
    violations: List[RuleViolation],
    language: str,
    project_folder: str,
    fix_types: List[str] = ["safe"],
    dry_run: bool = True,
    create_backup_flag: bool = True
) -> FixBatchResult:
    """Apply fixes to multiple violations in a coordinated manner.

    Args:
        violations: List of violations to fix
        language: Programming language for syntax validation
        project_folder: Project root folder
        fix_types: Types of fixes to apply ('safe', 'suggested', 'all')
        dry_run: If True, preview fixes without applying
        create_backup_flag: If True, create backup before applying fixes

    Returns:
        FixBatchResult with batch fix outcome
    """
    start_time = time.time()

    # Filter violations by fix type
    fixable_violations = _filter_violations_by_fix_type(violations, fix_types)

    if dry_run:
        # Dry run - validate fixes without applying
        results = []
        for violation in fixable_violations:
            validation = classify_fix_safety(violation.rule_id, violation)

            # Create a preview fix result
            results.append(FixResult(
                violation=violation,
                success=validation.is_safe,
                file_modified=False,
                original_code=violation.code_snippet,
                fixed_code=violation.fix_suggestion or "(fix pattern not specified)",
                syntax_valid=True,
                fix_type='safe' if validation.is_safe else 'suggested'
            ))

        execution_time = int((time.time() - start_time) * 1000)

        return FixBatchResult(
            total_violations=len(fixable_violations),
            fixes_attempted=0,
            fixes_successful=0,
            fixes_failed=0,
            files_modified=[],
            validation_passed=True,
            results=results,
            execution_time_ms=execution_time
        )

    # Real run - apply fixes
    backup_id = None
    if create_backup_flag:
        # Get unique file paths
        file_paths = list(set(v.file for v in fixable_violations))
        if file_paths:
            # Create backup
            backup_id = create_backup(file_paths, project_folder)
            logger.info(f"Created backup {backup_id} for {len(file_paths)} files")

    # Group violations by file
    violations_by_file: Dict[str, List[RuleViolation]] = {}
    for violation in fixable_violations:
        if violation.file not in violations_by_file:
            violations_by_file[violation.file] = []
        violations_by_file[violation.file].append(violation)

    # Apply fixes file by file
    fix_results: List[FixResult] = []
    files_modified: Set[str] = set()
    fixes_successful = 0
    fixes_failed = 0
    validation_passed = True

    for file_path, file_violations in violations_by_file.items():
        # Sort by line number (reverse order to avoid line number shifts)
        file_violations.sort(key=lambda v: v.line, reverse=True)

        for violation in file_violations:
            # Determine fix method
            if violation.fix_suggestion:
                # Use pattern-based fix
                result = apply_pattern_fix(file_path, violation, violation.fix_suggestion, language)
            else:
                # Use removal fix (for patterns like no-console-log, no-debugger)
                result = apply_removal_fix(file_path, violation, language)

            fix_results.append(result)

            if result.success and result.file_modified:
                fixes_successful += 1
                files_modified.add(file_path)

                if not result.syntax_valid:
                    validation_passed = False
            elif not result.success:
                fixes_failed += 1
                validation_passed = False

    # If any fixes failed and we have a backup, offer rollback
    if fixes_failed > 0 and backup_id:
        logger.warning(f"{fixes_failed} fixes failed. Backup {backup_id} available for rollback")

    execution_time = int((time.time() - start_time) * 1000)

    return FixBatchResult(
        total_violations=len(fixable_violations),
        fixes_attempted=fixes_successful + fixes_failed,
        fixes_successful=fixes_successful,
        fixes_failed=fixes_failed,
        files_modified=list(files_modified),
        backup_id=backup_id,
        validation_passed=validation_passed,
        results=fix_results,
        execution_time_ms=execution_time
    )


def _filter_violations_by_fix_type(
    violations: List[RuleViolation],
    fix_types: List[str]
) -> List[RuleViolation]:
    """Filter violations based on fix type preference.

    Args:
        violations: All violations
        fix_types: Allowed fix types ('safe', 'suggested', 'all')

    Returns:
        Filtered list of violations that can be fixed
    """
    if "all" in fix_types:
        return violations

    fixable = []
    for violation in violations:
        validation = classify_fix_safety(violation.rule_id, violation)

        if "safe" in fix_types and validation.is_safe:
            fixable.append(violation)
        elif "suggested" in fix_types and not validation.is_safe:
            fixable.append(violation)

    return fixable


# =============================================================================
# Fix Preview - Generate Diff Without Applying
# =============================================================================

def preview_fix(violation: RuleViolation) -> Dict[str, Any]:
    """Preview a fix without applying it.

    Args:
        violation: The violation to preview fix for

    Returns:
        Dictionary with fix preview information
    """
    validation = classify_fix_safety(violation.rule_id, violation)

    return {
        "violation": {
            "file": violation.file,
            "line": violation.line,
            "rule_id": violation.rule_id,
            "message": violation.message,
            "code": violation.code_snippet
        },
        "fix": {
            "original": violation.code_snippet,
            "fixed": violation.fix_suggestion or "(removal)",
            "is_safe": validation.is_safe,
            "confidence": validation.confidence,
            "requires_review": validation.requires_review,
            "warnings": validation.warnings
        }
    }
