"""Standards enforcement engine for linting rules.

This module provides functionality to execute linting rules against a codebase:
- Rule set loading (built-in and custom)
- Parallel rule execution with ThreadPoolExecutor
- Violation collection and grouping
- Severity filtering
- Human-readable reporting
"""

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from fnmatch import fnmatch
from pathlib import Path
from typing import Any, Dict, List, Set

import sentry_sdk
import yaml

from ast_grep_mcp.core.executor import stream_ast_grep_results
from ast_grep_mcp.core.logging import get_logger
from ast_grep_mcp.features.quality.rules import RULE_TEMPLATES, load_rules_from_project
from ast_grep_mcp.models.standards import EnforcementResult, LintingRule, RuleExecutionContext, RuleSet, RuleTemplate, RuleViolation

# =============================================================================
# Built-in Rule Sets
# =============================================================================

RULE_SETS: Dict[str, Dict[str, Any]] = {
    "recommended": {
        "description": "General best practices for clean, maintainable code",
        "priority": 100,
        "rules": [
            "no-var", "no-console-log", "no-double-equals",
            "no-empty-catch", "prefer-const", "no-bare-except",
            "no-mutable-defaults", "no-print-production",
            "no-debugger", "no-fixme-comments"
        ]
    },
    "security": {
        "description": "Security-focused rules to detect vulnerabilities",
        "priority": 200,  # Higher priority = run first
        "rules": [
            "no-eval-exec", "no-hardcoded-credentials", "no-sql-injection",
            "no-double-equals", "no-empty-catch", "no-bare-except",
            "no-string-exception", "no-assert-production",
            "proper-exception-handling"
        ]
    },
    "performance": {
        "description": "Performance anti-patterns and optimization opportunities",
        "priority": 50,
        "rules": [
            "no-magic-numbers"  # Placeholder - will expand with performance rules in future phases
        ]
    },
    "style": {
        "description": "Code style and formatting rules",
        "priority": 10,
        "rules": [
            "no-var", "prefer-const", "no-console-log",
            "no-print-production", "no-system-out", "no-any-type",
            "no-magic-numbers", "require-type-hints", "no-todo-comments"
        ]
    }
}


# =============================================================================
# Rule Set Loading
# =============================================================================

def template_to_linting_rule(template: RuleTemplate) -> LintingRule:
    """Convert RuleTemplate to LintingRule.

    Args:
        template: RuleTemplate object from RULE_TEMPLATES

    Returns:
        LintingRule object ready for execution
    """
    return LintingRule(
        id=template.id,
        language=template.language,
        severity=template.severity,
        message=template.message,
        pattern=template.pattern,
        note=template.note,
        fix=template.fix,
        constraints=template.constraints
    )


def load_custom_rules(project_folder: str, language: str) -> List[LintingRule]:
    """Load custom rules from .ast-grep-rules/ directory.

    Args:
        project_folder: Project root directory
        language: Target language for filtering

    Returns:
        List of LintingRule objects loaded from YAML files
    """
    logger = get_logger("load_custom_rules")

    # Use the rules.py function
    all_rules = load_rules_from_project(project_folder)

    # Filter by language
    filtered_rules = [r for r in all_rules if r.language == language]

    logger.info("custom_rules_loaded", count=len(filtered_rules), language=language)
    return filtered_rules


def _load_rules_from_templates(
    rule_ids: Set[str],
    language: str
) -> List[LintingRule]:
    """Load and filter rules from RULE_TEMPLATES by language.

    Args:
        rule_ids: Set of rule IDs to load
        language: Target language for filtering

    Returns:
        List of LintingRule objects matching the language
    """
    rules: List[LintingRule] = []
    for rule_id in rule_ids:
        if rule_id in RULE_TEMPLATES:
            template = RULE_TEMPLATES[rule_id]
            if template.language == language:
                rules.append(template_to_linting_rule(template))
    return rules


def _load_all_rules(language: str, logger: Any) -> RuleSet:
    """Load 'all' rule set - combines all built-in rule sets.

    Args:
        language: Target language for filtering
        logger: Logger instance

    Returns:
        RuleSet containing all built-in rules for the language
    """
    all_rule_ids: Set[str] = set()
    for set_config in RULE_SETS.values():
        all_rule_ids.update(set_config["rules"])

    rules = _load_rules_from_templates(all_rule_ids, language)

    logger.info("rule_set_loaded", rule_set="all", language=language, rules_count=len(rules))
    return RuleSet(
        name="all",
        description=f"All built-in rules for {language}",
        rules=rules,
        priority=100
    )


def _load_custom_rule_set(project_folder: str, language: str, logger: Any) -> RuleSet:
    """Load custom rule set from .ast-grep-rules/ directory.

    Args:
        project_folder: Project root for loading custom rules
        language: Target language for filtering
        logger: Logger instance

    Returns:
        RuleSet containing custom rules
    """
    custom_rules = load_custom_rules(project_folder, language)
    logger.info("rule_set_loaded", rule_set="custom", language=language, rules_count=len(custom_rules))
    return RuleSet(
        name="custom",
        description="Custom rules from .ast-grep-rules/",
        rules=custom_rules,
        priority=150
    )


def _load_builtin_rule_set(
    rule_set_name: str,
    language: str,
    logger: Any
) -> RuleSet:
    """Load a built-in rule set by name.

    Args:
        rule_set_name: Name of built-in rule set
        language: Target language for filtering
        logger: Logger instance

    Returns:
        RuleSet object with loaded rules

    Raises:
        ValueError: If rule set not found
    """
    if rule_set_name not in RULE_SETS:
        available = ", ".join(list(RULE_SETS.keys()) + ["custom", "all"])
        raise ValueError(
            f"Rule set '{rule_set_name}' not found. "
            f"Available: {available}"
        )

    set_config = RULE_SETS[rule_set_name]
    rule_ids = set(set_config["rules"])
    rules = _load_rules_from_templates(rule_ids, language)

    logger.info(
        "rule_set_loaded",
        rule_set=rule_set_name,
        language=language,
        rules_count=len(rules)
    )

    return RuleSet(
        name=rule_set_name,
        description=set_config["description"],
        rules=rules,
        priority=set_config["priority"]
    )


def load_rule_set(
    rule_set_name: str,
    project_folder: str,
    language: str
) -> RuleSet:
    """Load a built-in or custom rule set.

    Args:
        rule_set_name: Name of rule set ('recommended', 'security', 'custom', 'all')
        project_folder: Project root for loading custom rules
        language: Target language for filtering rules

    Returns:
        RuleSet object with loaded rules

    Raises:
        ValueError: If rule set not found or language unsupported
    """
    logger = get_logger("load_rule_set")

    # Dispatch to appropriate loader based on rule set type
    if rule_set_name == "all":
        return _load_all_rules(language, logger)

    if rule_set_name == "custom":
        return _load_custom_rule_set(project_folder, language, logger)

    return _load_builtin_rule_set(rule_set_name, language, logger)


# =============================================================================
# Rule Execution
# =============================================================================

def parse_match_to_violation(match: Dict[str, Any], rule: LintingRule) -> RuleViolation:
    """Parse ast-grep JSON match into RuleViolation.

    Args:
        match: JSON match object from ast-grep
        rule: Rule that generated this match

    Returns:
        RuleViolation object
    """
    # Extract range information
    range_info = match.get("range", {})
    start = range_info.get("start", {})
    end = range_info.get("end", {})

    # Extract metavariables if present
    # ast-grep returns format: {"single": {"NAME": {"text": "..."}}, "multi": {...}}
    meta_vars = None
    if "metaVariables" in match:
        meta_vars = {}
        meta_data = match["metaVariables"]
        # Handle "single" metavariables (single captures like $NAME)
        if "single" in meta_data and isinstance(meta_data["single"], dict):
            for var_name, var_info in meta_data["single"].items():
                if isinstance(var_info, dict) and "text" in var_info:
                    meta_vars[var_name] = var_info["text"]
        # Handle "multi" metavariables (multiple captures like $$$ARGS)
        if "multi" in meta_data and isinstance(meta_data["multi"], dict):
            for var_name, var_list in meta_data["multi"].items():
                if isinstance(var_list, list):
                    meta_vars[var_name] = [v.get("text", "") for v in var_list if isinstance(v, dict)]

    return RuleViolation(
        file=match.get("file", ""),
        line=start.get("line", 0),
        column=start.get("column", 0),
        end_line=end.get("line", 0),
        end_column=end.get("column", 0),
        severity=rule.severity,
        rule_id=rule.id,
        message=rule.message,
        code_snippet=match.get("text", ""),
        fix_suggestion=rule.fix,
        meta_vars=meta_vars
    )


def should_exclude_file(file_path: str, exclude_patterns: List[str]) -> bool:
    """Check if file should be excluded based on patterns.

    Args:
        file_path: Absolute file path
        exclude_patterns: List of glob patterns to exclude

    Returns:
        True if file should be excluded
    """
    for pattern in exclude_patterns:
        # Handle recursive patterns like **/node_modules/**
        if "**" in pattern:
            pattern_parts = pattern.split("**")
            # Check if any non-empty part is in the file path
            if any(part.strip("/") and part.strip("/") in file_path for part in pattern_parts if part):
                return True
        elif fnmatch(file_path, pattern) or fnmatch(str(Path(file_path).name), pattern):
            return True

    return False


def execute_rule(
    rule: LintingRule,
    context: RuleExecutionContext
) -> List[RuleViolation]:
    """Execute a single rule and return violations.

    Args:
        rule: LintingRule to execute
        context: Execution context with project settings

    Returns:
        List of RuleViolation objects found by this rule
    """
    logger = context.logger

    try:
        # Build ast-grep command arguments
        yaml_rule = rule.to_yaml_dict()
        # Note: --inline-rules expects a single rule, not a rules array
        yaml_str = yaml.safe_dump(yaml_rule)

        args = [
            "--inline-rules", yaml_str,
            "--json=stream"
        ]
        # Note: --lang is not needed here as language is specified in the YAML rule itself

        # Add project folder to scan
        args.append(context.project_folder)

        # Execute using streaming parser
        violations: List[RuleViolation] = []

        with sentry_sdk.start_span(op="execute_rule", description=f"Rule: {rule.id}"):
            matches = list(stream_ast_grep_results(
                "scan",
                args,
                max_results=context.max_violations if context.max_violations > 0 else 0,
                progress_interval=100
            ))

        # Parse matches into violations
        for match in matches:
            violation = parse_match_to_violation(match, rule)

            # Apply exclude patterns
            if should_exclude_file(violation.file, context.exclude_patterns):
                continue

            violations.append(violation)

            # Stop if max_violations reached
            if context.max_violations > 0 and len(violations) >= context.max_violations:
                break

        logger.info(
            "rule_executed",
            rule_id=rule.id,
            violations_found=len(violations)
        )

        return violations

    except Exception as e:
        logger.error("rule_execution_failed", rule_id=rule.id, error=str(e))
        sentry_sdk.capture_exception(e, extras={"rule_id": rule.id})
        # Don't fail entire scan if one rule fails
        return []


def _should_stop_execution(
    violations_count: int,
    max_violations: int
) -> bool:
    """Check if execution should stop due to violation limit."""
    return max_violations > 0 and violations_count >= max_violations


def _execute_rule_with_limit(
    rule: LintingRule,
    context: RuleExecutionContext,
    all_violations: List[RuleViolation],
    violations_lock: threading.Lock
) -> List[RuleViolation]:
    """Execute a single rule with violation limit checking.

    Args:
        rule: The linting rule to execute
        context: Execution context
        all_violations: Shared list of all violations (for limit checking)
        violations_lock: Lock for thread-safe access to all_violations

    Returns:
        List of violations found by this rule
    """
    # Check limit before executing
    with violations_lock:
        if _should_stop_execution(len(all_violations), context.max_violations):
            context.logger.info("max_violations_reached", current=len(all_violations))
            return []

    # Execute the rule
    return execute_rule(rule, context)


def _process_rule_result(
    future: Any,
    futures: Dict[Any, LintingRule],
    all_violations: List[RuleViolation],
    violations_lock: threading.Lock,
    context: RuleExecutionContext
) -> bool:
    """Process the result from a completed rule execution future.

    Args:
        future: Completed future
        futures: Map of all futures to their rules
        all_violations: List to append violations to
        violations_lock: Lock for thread-safe access
        context: Execution context for logging and limits

    Returns:
        True if execution should continue, False if max violations reached
    """
    try:
        violations = future.result()

        with violations_lock:
            all_violations.extend(violations)

            # Check if we should stop
            if _should_stop_execution(len(all_violations), context.max_violations):
                # Cancel remaining futures
                for f in futures:
                    if not f.done():
                        f.cancel()
                return False  # Stop processing

    except Exception as e:
        rule = futures[future]
        context.logger.warning("rule_batch_execution_failed", rule_id=rule.id, error=str(e))

    return True  # Continue processing


def execute_rules_batch(
    rules: List[LintingRule],
    context: RuleExecutionContext
) -> List[RuleViolation]:
    """Execute multiple rules in parallel.

    Args:
        rules: List of LintingRule objects to execute
        context: Execution context

    Returns:
        Combined list of all violations found
    """
    all_violations: List[RuleViolation] = []
    violations_lock = threading.Lock()

    # Execute rules in parallel
    with ThreadPoolExecutor(max_workers=context.max_threads) as executor:
        # Submit all rules for execution
        futures = {
            executor.submit(
                _execute_rule_with_limit,
                rule,
                context,
                all_violations,
                violations_lock
            ): rule
            for rule in rules
        }

        # Process results as they complete
        for future in as_completed(futures):
            should_continue = _process_rule_result(
                future,
                futures,
                all_violations,
                violations_lock,
                context
            )

            if not should_continue:
                break

    return all_violations


# =============================================================================
# Violation Processing
# =============================================================================

def group_violations_by_file(
    violations: List[RuleViolation]
) -> Dict[str, List[RuleViolation]]:
    """Group violations by file path.

    Args:
        violations: List of all violations

    Returns:
        Dictionary mapping file paths to their violations
    """
    grouped: Dict[str, List[RuleViolation]] = {}

    for violation in violations:
        if violation.file not in grouped:
            grouped[violation.file] = []
        grouped[violation.file].append(violation)

    # Sort violations within each file by line number
    for file_path in grouped:
        grouped[file_path].sort(key=lambda v: (v.line, v.column))

    return grouped


def group_violations_by_severity(
    violations: List[RuleViolation]
) -> Dict[str, List[RuleViolation]]:
    """Group violations by severity level.

    Args:
        violations: List of all violations

    Returns:
        Dictionary mapping severity levels to their violations
    """
    grouped: Dict[str, List[RuleViolation]] = {
        "error": [],
        "warning": [],
        "info": []
    }

    for violation in violations:
        if violation.severity in grouped:
            grouped[violation.severity].append(violation)

    return grouped


def group_violations_by_rule(
    violations: List[RuleViolation]
) -> Dict[str, List[RuleViolation]]:
    """Group violations by rule ID.

    Args:
        violations: List of all violations

    Returns:
        Dictionary mapping rule IDs to their violations
    """
    grouped: Dict[str, List[RuleViolation]] = {}

    for violation in violations:
        if violation.rule_id not in grouped:
            grouped[violation.rule_id] = []
        grouped[violation.rule_id].append(violation)

    return grouped


def filter_violations_by_severity(
    violations: List[RuleViolation],
    severity_threshold: str
) -> List[RuleViolation]:
    """Filter violations to only include >= severity threshold.

    Args:
        violations: All violations
        severity_threshold: Minimum severity ('error', 'warning', 'info')

    Returns:
        Filtered list of violations
    """
    severity_order = {"info": 0, "warning": 1, "error": 2}
    min_level = severity_order.get(severity_threshold, 0)

    return [
        v for v in violations
        if severity_order.get(v.severity, 0) >= min_level
    ]


# =============================================================================
# Reporting
# =============================================================================

def format_violation_report(result: EnforcementResult) -> str:
    """Format enforcement result as human-readable text report.

    Args:
        result: EnforcementResult object

    Returns:
        Formatted text report
    """
    lines: List[str] = []

    # Summary header
    lines.append("=" * 80)
    lines.append("CODE STANDARDS ENFORCEMENT REPORT")
    lines.append("=" * 80)
    lines.append("")

    summary = result.summary
    lines.append(f"Files Scanned: {summary['files_scanned']}")
    lines.append(f"Rules Executed: {len(result.rules_executed)}")
    lines.append(f"Total Violations: {summary['total_violations']}")
    lines.append(f"Execution Time: {summary['execution_time_ms']}ms")
    lines.append("")

    # Severity breakdown
    lines.append("Violations by Severity:")
    for severity in ["error", "warning", "info"]:
        count = summary["by_severity"].get(severity, 0)
        if count > 0:
            lines.append(f"  {severity.upper()}: {count}")

    lines.append("")

    # Group by file
    if result.violations_by_file:
        lines.append("Violations by File:")
        lines.append("-" * 80)

        for file_path, violations in sorted(result.violations_by_file.items()):
            lines.append(f"\n{file_path} ({len(violations)} violations)")

            for v in violations:
                lines.append(
                    f"  Line {v.line}:{v.column} [{v.severity.upper()}] {v.rule_id}"
                )
                lines.append(f"    {v.message}")
                if v.fix_suggestion:
                    lines.append(f"    Fix: {v.fix_suggestion}")
                lines.append("")

    else:
        lines.append("\nNo violations found!")

    lines.append("=" * 80)

    return "\n".join(lines)


# =============================================================================
# Main Enforcement Function
# =============================================================================

def enforce_standards_impl(
    project_folder: str,
    language: str,
    rule_set: str,
    custom_rules: List[str],
    include_patterns: List[str],
    exclude_patterns: List[str],
    severity_threshold: str,
    max_violations: int,
    max_threads: int
) -> EnforcementResult:
    """Enforce coding standards by executing linting rules against a project.

    Args:
        project_folder: Absolute path to project
        language: Programming language
        rule_set: Rule set name ('recommended', 'security', 'performance', 'style', 'custom', 'all')
        custom_rules: List of custom rule IDs (used with rule_set='custom')
        include_patterns: Glob patterns for files to include
        exclude_patterns: Glob patterns for files to exclude
        severity_threshold: Only report violations >= this severity
        max_violations: Maximum violations to find (0 = unlimited)
        max_threads: Number of parallel threads for rule execution

    Returns:
        EnforcementResult with all violations and summary statistics
    """
    import time
    logger = get_logger("enforce_standards")
    start_time = time.time()

    # Validate project folder exists
    project_path = Path(project_folder).resolve()
    if not project_path.exists():
        raise ValueError(f"Project folder does not exist: {project_folder}")

    # Load rule set
    with sentry_sdk.start_span(op="load_rule_set", description=f"Set: {rule_set}"):
        if rule_set == "custom" and custom_rules:
            # Load specific custom rules by ID
            all_custom = load_custom_rules(str(project_path), language)
            rules = [r for r in all_custom if r.id in custom_rules]

            if not rules:
                raise ValueError(
                    f"No custom rules found matching IDs: {custom_rules}. "
                    f"Available: {[r.id for r in all_custom]}"
                )

            rule_set_obj = RuleSet(
                name="custom",
                description=f"Custom rules: {', '.join(custom_rules)}",
                rules=rules,
                priority=150
            )
        else:
            rule_set_obj = load_rule_set(rule_set, str(project_path), language)

    if not rule_set_obj.rules:
        # Return empty result if no rules
        return EnforcementResult(
            summary={
                "total_violations": 0,
                "by_severity": {"error": 0, "warning": 0, "info": 0},
                "by_file": {},
                "files_scanned": 0,
                "rules_executed": 0,
                "execution_time_ms": 0
            },
            violations=[],
            violations_by_file={},
            violations_by_severity={"error": [], "warning": [], "info": []},
            violations_by_rule={},
            rules_executed=[],
            execution_time_ms=0,
            files_scanned=0
        )

    logger.info(
        "rules_loaded",
        rule_set=rule_set,
        rules_count=len(rule_set_obj.rules)
    )

    # Create execution context
    context = RuleExecutionContext(
        project_folder=str(project_path),
        language=language,
        include_patterns=include_patterns,
        exclude_patterns=exclude_patterns,
        max_violations=max_violations,
        max_threads=max_threads,
        logger=logger
    )

    # Execute rules in parallel
    with sentry_sdk.start_span(op="execute_rules", description=f"Rules: {len(rule_set_obj.rules)}"):
        all_violations = execute_rules_batch(rule_set_obj.rules, context)

    # Filter by severity threshold
    filtered_violations = filter_violations_by_severity(all_violations, severity_threshold)

    # Group violations
    violations_by_file = group_violations_by_file(filtered_violations)
    violations_by_severity = group_violations_by_severity(filtered_violations)
    violations_by_rule = group_violations_by_rule(filtered_violations)

    # Calculate summary
    execution_time = time.time() - start_time
    duration_ms = int(execution_time * 1000)

    summary = {
        "total_violations": len(filtered_violations),
        "by_severity": {
            "error": len(violations_by_severity["error"]),
            "warning": len(violations_by_severity["warning"]),
            "info": len(violations_by_severity["info"])
        },
        "by_file": {
            file_path: len(violations)
            for file_path, violations in violations_by_file.items()
        },
        "files_scanned": len(violations_by_file),
        "rules_executed": len(rule_set_obj.rules),
        "execution_time_ms": duration_ms
    }

    # Build result
    result = EnforcementResult(
        summary=summary,
        violations=filtered_violations,
        violations_by_file=violations_by_file,
        violations_by_severity=violations_by_severity,
        violations_by_rule=violations_by_rule,
        rules_executed=[r.id for r in rule_set_obj.rules],
        execution_time_ms=duration_ms,
        files_scanned=len(violations_by_file)
    )

    logger.info(
        "enforcement_completed",
        total_violations=len(filtered_violations),
        files_scanned=len(violations_by_file),
        execution_time_seconds=round(execution_time, 3)
    )

    return result
