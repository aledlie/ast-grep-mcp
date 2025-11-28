"""MCP tool definitions for code quality and standards features.

This module registers MCP tools for:
- detect_code_smells: Code smell detection
- create_linting_rule: Create custom linting rules
- list_rule_templates: Browse pre-built rule templates
- enforce_standards: Standards enforcement engine
"""

import time
from typing import Any, Dict, List, Optional

import sentry_sdk
import yaml
from mcp.server.fastmcp import FastMCP
from pydantic import Field

from ast_grep_mcp.core.logging import get_logger
from ast_grep_mcp.features.quality.enforcer import enforce_standards_impl, format_violation_report
from ast_grep_mcp.features.quality.fixer import apply_fixes_batch, preview_fix
from ast_grep_mcp.features.quality.reporter import generate_quality_report_impl
from ast_grep_mcp.features.quality.rules import RULE_TEMPLATES, create_rule_from_template, get_available_templates, save_rule_to_project
from ast_grep_mcp.features.quality.security_scanner import detect_security_issues_impl
from ast_grep_mcp.features.quality.validator import validate_rule_definition
from ast_grep_mcp.models.standards import EnforcementResult, LintingRule, RuleStorageError, RuleValidationError, RuleViolation, SecurityIssue


def create_linting_rule_tool(
    rule_name: str,
    description: str,
    pattern: str,
    severity: str,
    language: str,
    suggested_fix: Optional[str] = None,
    note: Optional[str] = None,
    save_to_project: bool = False,
    project_folder: Optional[str] = None,
    use_template: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a custom linting rule using ast-grep patterns.

    This function allows you to define custom code quality rules that can be enforced
    across your codebase. Rules can detect code smells, anti-patterns, security
    vulnerabilities, or enforce style guidelines.

    **Templates:** Use `use_template` parameter to start from a pre-built template
    (see list_rule_templates_tool).

    **Pattern Syntax Examples:**
    - `console.log($$$)` - matches any console.log call
    - `var $NAME = $$$` - matches var declarations
    - `except:` - matches bare except clauses in Python

    Args:
        rule_name: Unique rule identifier (e.g., 'no-console-log')
        description: Human-readable description of what the rule checks
        pattern: ast-grep pattern to match (e.g., 'console.log($$$)')
        severity: Severity level: 'error', 'warning', or 'info'
        language: Target language (python, typescript, javascript, java, etc.)
        suggested_fix: Optional replacement pattern or fix suggestion
        note: Additional note or explanation
        save_to_project: If True, save rule to project's .ast-grep-rules/
        project_folder: Project folder (required if save_to_project=True)
        use_template: Optional template ID to use as base

    Returns:
        Dictionary containing rule definition, validation results, saved path, and YAML
    """
    logger = get_logger("tool.create_linting_rule")
    start_time = time.time()

    logger.info(
        "tool_invoked",
        tool="create_linting_rule",
        rule_name=rule_name,
        language=language,
        severity=severity,
        use_template=use_template,
        save_to_project=save_to_project
    )

    try:
        with sentry_sdk.start_span(op="create_linting_rule", description="Create custom linting rule"):
            # If using a template, create from template
            if use_template:
                overrides = {
                    'language': language,
                    'severity': severity,
                    'message': description,
                    'pattern': pattern,
                    'note': note,
                    'fix': suggested_fix
                }
                # Remove None values
                overrides = {k: v for k, v in overrides.items() if v is not None}

                rule = create_rule_from_template(use_template, rule_name, overrides)
                logger.info("rule_created_from_template", template_id=use_template)
            else:
                # Create rule from scratch
                rule = LintingRule(
                    id=rule_name,
                    language=language,
                    severity=severity,
                    message=description,
                    pattern=pattern,
                    note=note,
                    fix=suggested_fix
                )

            # Validate the rule
            with sentry_sdk.start_span(op="validate_rule", description="Validate rule definition"):
                validation_result = validate_rule_definition(rule)

            # Save to project if requested
            saved_path: Optional[str] = None
            if save_to_project:
                if not project_folder:
                    raise ValueError(
                        "project_folder is required when save_to_project=True"
                    )

                if not validation_result.is_valid:
                    raise RuleValidationError(
                        f"Cannot save invalid rule. Errors: {', '.join(validation_result.errors)}"
                    )

                with sentry_sdk.start_span(op="save_rule", description="Save rule to project"):
                    saved_path = save_rule_to_project(rule, project_folder)

            # Convert to YAML for output
            rule_dict = rule.to_yaml_dict()
            yaml_str = yaml.dump(rule_dict, default_flow_style=False, sort_keys=False)

            execution_time = time.time() - start_time
            logger.info(
                "tool_completed",
                tool="create_linting_rule",
                execution_time_seconds=round(execution_time, 3),
                rule_id=rule.id,
                is_valid=validation_result.is_valid,
                saved=saved_path is not None
            )

            return {
                "rule": {
                    "id": rule.id,
                    "language": rule.language,
                    "severity": rule.severity,
                    "message": rule.message,
                    "pattern": rule.pattern,
                    "note": rule.note,
                    "fix": rule.fix,
                    "constraints": rule.constraints
                },
                "validation": {
                    "is_valid": validation_result.is_valid,
                    "errors": validation_result.errors,
                    "warnings": validation_result.warnings
                },
                "saved_to": saved_path,
                "yaml": yaml_str
            }

    except (RuleValidationError, RuleStorageError, ValueError) as e:
        execution_time = time.time() - start_time
        logger.error(
            "tool_failed",
            tool="create_linting_rule",
            execution_time_seconds=round(execution_time, 3),
            error=str(e)[:200]
        )
        sentry_sdk.capture_exception(e, extras={
            "tool": "create_linting_rule",
            "rule_name": rule_name,
            "language": language,
            "execution_time_seconds": round(execution_time, 3)
        })
        raise


def list_rule_templates_tool(
    language: Optional[str] = None,
    category: Optional[str] = None
) -> Dict[str, Any]:
    """
    List available pre-built rule templates.

    This function returns a library of pre-built linting rules that can be used
    as-is or customized for your needs. Templates cover common patterns across
    multiple languages including JavaScript/TypeScript, Python, and Java.

    **Template Categories:**
    - `general`: General code quality and best practices
    - `security`: Security vulnerabilities and risks
    - `performance`: Performance anti-patterns
    - `style`: Code style and consistency

    Args:
        language: Filter by language (python, typescript, javascript, java, etc.)
        category: Filter by category (general, security, performance, style)

    Returns:
        Dictionary with total count, available languages/categories, and template list
    """
    logger = get_logger("tool.list_rule_templates")
    start_time = time.time()

    logger.info(
        "tool_invoked",
        tool="list_rule_templates",
        language=language,
        category=category
    )

    try:
        with sentry_sdk.start_span(op="list_templates", description="Get rule templates"):
            templates = get_available_templates(language=language, category=category)

            # Get unique languages and categories from all templates
            all_templates = list(RULE_TEMPLATES.values())
            all_languages = sorted(set(t.language for t in all_templates))
            all_categories = sorted(set(t.category for t in all_templates))

            # Convert templates to dict format
            template_dicts = [
                {
                    "id": t.id,
                    "name": t.name,
                    "description": t.description,
                    "language": t.language,
                    "severity": t.severity,
                    "pattern": t.pattern,
                    "message": t.message,
                    "note": t.note,
                    "fix": t.fix,
                    "category": t.category
                }
                for t in templates
            ]

            execution_time = time.time() - start_time
            logger.info(
                "tool_completed",
                tool="list_rule_templates",
                execution_time_seconds=round(execution_time, 3),
                total_templates=len(template_dicts),
                filtered=bool(language or category)
            )

            return {
                "total_templates": len(template_dicts),
                "languages": all_languages,
                "categories": all_categories,
                "applied_filters": {
                    "language": language,
                    "category": category
                },
                "templates": template_dicts
            }

    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(
            "tool_failed",
            tool="list_rule_templates",
            execution_time_seconds=round(execution_time, 3),
            error=str(e)[:200]
        )
        sentry_sdk.capture_exception(e, extras={
            "tool": "list_rule_templates",
            "language": language,
            "category": category,
            "execution_time_seconds": round(execution_time, 3)
        })
        raise


def enforce_standards_tool(
    project_folder: str,
    language: str,
    rule_set: str = "recommended",
    custom_rules: List[str] | None = None,
    include_patterns: List[str] | None = None,
    exclude_patterns: List[str] | None = None,
    severity_threshold: str = "info",
    max_violations: int = 100,
    max_threads: int = 4,
    output_format: str = "json"
) -> Dict[str, Any]:
    """
    Enforce coding standards by executing linting rules against a project.

    This function runs a set of linting rules (built-in or custom) against your codebase
    and reports all violations with file locations, severity levels, and fix suggestions.

    **Rule Sets:**
    - `recommended`: General best practices (10 rules)
    - `security`: Security-focused rules (9 rules)
    - `performance`: Performance anti-patterns
    - `style`: Code style and formatting rules (9 rules)
    - `custom`: Load custom rules from .ast-grep-rules/
    - `all`: All built-in rules for the language

    Args:
        project_folder: The absolute path to the project folder to scan
        language: The programming language (python, typescript, javascript, java)
        rule_set: Rule set to use: 'recommended', 'security', 'performance', 'style', 'custom', 'all'
        custom_rules: List of custom rule IDs from .ast-grep-rules/ (used with rule_set='custom')
        include_patterns: Glob patterns for files to include (e.g., ['src/**/*.py'])
        exclude_patterns: Glob patterns for files to exclude
        severity_threshold: Only report violations >= this severity ('error', 'warning', 'info')
        max_violations: Maximum violations to find (0 = unlimited). Stops execution early when reached.
        max_threads: Number of parallel threads for rule execution (default: 4)
        output_format: Output format: 'json' (structured data) or 'text' (human-readable report)

    Returns:
        Dictionary with summary, violations, and execution statistics

    Example usage:
        enforce_standards_tool(project_folder="/path/to/project", language="python")
        enforce_standards_tool(project_folder="/path/to/project", language="typescript", rule_set="security")
    """
    # Set defaults
    if custom_rules is None:
        custom_rules = []
    if include_patterns is None:
        include_patterns = ["**/*"]
    if exclude_patterns is None:
        exclude_patterns = [
            "**/node_modules/**", "**/__pycache__/**", "**/venv/**",
            "**/.venv/**", "**/site-packages/**", "**/dist/**",
            "**/build/**", "**/.git/**", "**/coverage/**"
        ]

    logger = get_logger("tool.enforce_standards")
    start_time = time.time()

    logger.info(
        "tool_invoked",
        tool="enforce_standards",
        project_folder=project_folder,
        language=language,
        rule_set=rule_set,
        custom_rules_count=len(custom_rules),
        max_violations=max_violations,
        max_threads=max_threads
    )

    try:
        # Validate inputs
        if severity_threshold not in ["error", "warning", "info"]:
            raise ValueError(
                f"Invalid severity_threshold: {severity_threshold}. "
                "Must be 'error', 'warning', or 'info'."
            )

        if output_format not in ["json", "text"]:
            raise ValueError(
                f"Invalid output_format: {output_format}. "
                "Must be 'json' or 'text'."
            )

        # Execute enforcement
        result = enforce_standards_impl(
            project_folder=project_folder,
            language=language,
            rule_set=rule_set,
            custom_rules=custom_rules,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
            severity_threshold=severity_threshold,
            max_violations=max_violations,
            max_threads=max_threads
        )

        execution_time = time.time() - start_time

        logger.info(
            "tool_completed",
            tool="enforce_standards",
            execution_time_seconds=round(execution_time, 3),
            total_violations=result.summary["total_violations"],
            files_scanned=result.files_scanned
        )

        # Format output
        if output_format == "text":
            return {
                "summary": result.summary,
                "report": format_violation_report(result)
            }
        else:
            # JSON format - return full structured data
            return {
                "summary": result.summary,
                "violations": [
                    {
                        "file": v.file,
                        "line": v.line,
                        "column": v.column,
                        "end_line": v.end_line,
                        "end_column": v.end_column,
                        "severity": v.severity,
                        "rule_id": v.rule_id,
                        "message": v.message,
                        "code_snippet": v.code_snippet,
                        "fix_suggestion": v.fix_suggestion,
                        "meta_vars": v.meta_vars
                    }
                    for v in result.violations
                ],
                "violations_by_file": {
                    file: [
                        {
                            "line": v.line,
                            "severity": v.severity,
                            "rule_id": v.rule_id,
                            "message": v.message
                        }
                        for v in violations
                    ]
                    for file, violations in result.violations_by_file.items()
                },
                "rules_executed": result.rules_executed,
                "execution_time_ms": result.execution_time_ms
            }

    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(
            "tool_failed",
            tool="enforce_standards",
            execution_time_seconds=round(execution_time, 3),
            error=str(e)[:200]
        )
        sentry_sdk.capture_exception(e, extras={
            "tool": "enforce_standards",
            "project_folder": project_folder,
            "language": language,
            "rule_set": rule_set,
            "execution_time_seconds": round(execution_time, 3)
        })
        raise


def apply_standards_fixes_tool(
    violations: List[Dict[str, Any]],
    language: str,
    fix_types: List[str] | None = None,
    dry_run: bool = True,
    create_backup: bool = True
) -> Dict[str, Any]:
    """
    Automatically fix code quality violations detected by enforce_standards.

    This function takes violations from enforce_standards and applies fixes automatically.
    It supports safe fixes (guaranteed-safe), suggested fixes (may need review), or all fixes.

    **Fix Types:**
    - `safe`: Only apply guaranteed-safe fixes (e.g., var → const, console.log removal)
    - `suggested`: Apply fixes that may need review (e.g., exception handling changes)
    - `all`: Apply all available fixes

    **Safety:**
    - All fixes are validated with syntax checking
    - Backup is created automatically (unless disabled)
    - Dry-run mode previews changes without applying
    - Failed fixes are rolled back automatically

    Args:
        violations: List of violations from enforce_standards (each must have 'file', 'line', 'rule_id', etc.)
        language: Programming language for syntax validation
        fix_types: Types of fixes to apply ('safe', 'suggested', 'all')
        dry_run: If True, preview fixes without applying them
        create_backup: If True, create backup before applying fixes

    Returns:
        Dictionary with fix results, backup ID, and statistics

    Example usage:
        # First, find violations
        result = enforce_standards_tool(project_folder="/path", language="python")

        # Preview fixes (dry run)
        preview = apply_standards_fixes_tool(
            violations=result["violations"],
            language="python",
            fix_types=["safe"],
            dry_run=True
        )

        # Apply safe fixes
        fixed = apply_standards_fixes_tool(
            violations=result["violations"],
            language="python",
            fix_types=["safe"],
            dry_run=False,
            create_backup=True
        )
    """
    # Set defaults
    if fix_types is None:
        fix_types = ["safe"]

    logger = get_logger("tool.apply_standards_fixes")
    start_time = time.time()

    logger.info(
        "tool_invoked",
        tool="apply_standards_fixes",
        violations_count=len(violations),
        language=language,
        fix_types=fix_types,
        dry_run=dry_run,
        create_backup=create_backup
    )

    try:
        # Convert dictionaries to RuleViolation objects
        violation_objects = []
        for v_dict in violations:
            violation = RuleViolation(
                file=v_dict["file"],
                line=v_dict["line"],
                column=v_dict.get("column", 1),
                end_line=v_dict.get("end_line", v_dict["line"]),
                end_column=v_dict.get("end_column", 1),
                severity=v_dict["severity"],
                rule_id=v_dict["rule_id"],
                message=v_dict["message"],
                code_snippet=v_dict["code_snippet"],
                fix_suggestion=v_dict.get("fix_suggestion"),
                meta_vars=v_dict.get("meta_vars")
            )
            violation_objects.append(violation)

        # Apply fixes
        # Extract project folder from the first violation's file path
        if violations:
            first_file = violations[0].get("file", "")
            import os
            # Get the common prefix of all file paths as the project folder
            all_files = [v.get("file", "") for v in violations if v.get("file")]
            if all_files:
                common_prefix = os.path.commonprefix(all_files)
                # Get the directory part
                project_folder_inferred = os.path.dirname(common_prefix) if not os.path.isdir(common_prefix) else common_prefix
            else:
                project_folder_inferred = os.getcwd()
        else:
            project_folder_inferred = os.getcwd()

        result = apply_fixes_batch(
            violations=violation_objects,
            language=language,
            project_folder=project_folder_inferred,
            fix_types=fix_types,
            dry_run=dry_run,
            create_backup_flag=create_backup
        )

        execution_time = time.time() - start_time

        logger.info(
            "tool_completed",
            tool="apply_standards_fixes",
            execution_time_seconds=round(execution_time, 3),
            total_violations=result.total_violations,
            fixes_attempted=result.fixes_attempted,
            fixes_successful=result.fixes_successful,
            fixes_failed=result.fixes_failed,
            dry_run=dry_run
        )

        # Format output
        return {
            "summary": {
                "total_violations": result.total_violations,
                "fixes_attempted": result.fixes_attempted,
                "fixes_successful": result.fixes_successful,
                "fixes_failed": result.fixes_failed,
                "files_modified": len(result.files_modified),
                "validation_passed": result.validation_passed,
                "dry_run": dry_run
            },
            "backup_id": result.backup_id,
            "files_modified": result.files_modified,
            "results": [
                {
                    "file": r.violation.file,
                    "line": r.violation.line,
                    "rule_id": r.violation.rule_id,
                    "success": r.success,
                    "file_modified": r.file_modified,
                    "original_code": r.original_code,
                    "fixed_code": r.fixed_code,
                    "syntax_valid": r.syntax_valid,
                    "error": r.error,
                    "fix_type": r.fix_type
                }
                for r in result.results
            ],
            "execution_time_ms": result.execution_time_ms
        }

    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(
            "tool_failed",
            tool="apply_standards_fixes",
            execution_time_seconds=round(execution_time, 3),
            error=str(e)[:200]
        )
        sentry_sdk.capture_exception(e, extras={
            "tool": "apply_standards_fixes",
            "violations_count": len(violations),
            "language": language,
            "fix_types": fix_types,
            "execution_time_seconds": round(execution_time, 3)
        })
        raise


def generate_quality_report_tool(
    enforcement_result: Dict[str, Any],
    project_name: str = "Project",
    output_format: str = "markdown",
    include_violations: bool = True,
    include_code_snippets: bool = False,
    save_to_file: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate a comprehensive code quality report from enforcement results.

    This function creates professional quality reports in Markdown or JSON format,
    summarizing violations, top issues, and providing actionable recommendations.

    **Output Formats:**
    - `markdown`: Human-readable report with tables and sections
    - `json`: Machine-readable structured data

    **Report Sections:**
    - Summary statistics (violations by severity)
    - Violations by severity level
    - Top issues by rule
    - Files with most violations
    - Recommendations and auto-fix suggestions

    Args:
        enforcement_result: Result dictionary from enforce_standards tool
        project_name: Name of the project for report header
        output_format: Report format ('markdown' or 'json')
        include_violations: Whether to include detailed violation listings
        include_code_snippets: Whether to include code snippets (JSON only)
        save_to_file: Optional file path to save the report

    Returns:
        Dictionary with report content and metadata

    Example usage:
        # Run enforcement
        result = enforce_standards(project_folder="/path", language="python")

        # Generate Markdown report
        report = generate_quality_report(
            enforcement_result=result,
            project_name="My Project",
            output_format="markdown",
            save_to_file="quality-report.md"
        )

        print(report["content"])
    """
    logger = get_logger("tool.generate_quality_report")
    start_time = time.time()

    logger.info(
        "tool_invoked",
        tool="generate_quality_report",
        project_name=project_name,
        output_format=output_format,
        save_to_file=save_to_file
    )

    try:
        # Convert dictionary to EnforcementResult
        # Note: enforcement_result should already have the structure we need
        # We'll use it directly in generate_quality_report_impl

        # For now, create a simplified approach - pass the dict directly
        # and let generate_quality_report_impl handle it

        result_obj = _dict_to_enforcement_result(enforcement_result)

        # Generate report
        report = generate_quality_report_impl(
            result=result_obj,
            project_name=project_name,
            output_format=output_format,
            include_violations=include_violations,
            include_code_snippets=include_code_snippets,
            save_to_file=save_to_file
        )

        execution_time = time.time() - start_time

        logger.info(
            "tool_completed",
            tool="generate_quality_report",
            execution_time_seconds=round(execution_time, 3),
            output_format=output_format,
            saved=save_to_file is not None
        )

        return report

    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(
            "tool_failed",
            tool="generate_quality_report",
            execution_time_seconds=round(execution_time, 3),
            error=str(e)[:200]
        )
        sentry_sdk.capture_exception(e, extras={
            "tool": "generate_quality_report",
            "project_name": project_name,
            "output_format": output_format,
            "execution_time_seconds": round(execution_time, 3)
        })
        raise


def _dict_to_enforcement_result(data: Dict[str, Any]) -> EnforcementResult:
    """Convert enforcement result dictionary to EnforcementResult object.

    Args:
        data: Dictionary from enforce_standards tool

    Returns:
        EnforcementResult object
    """
    # Convert violations
    violations = []
    for v_dict in data.get("violations", []):
        violation = RuleViolation(
            file=v_dict["file"],
            line=v_dict["line"],
            column=v_dict.get("column", 1),
            end_line=v_dict.get("end_line", v_dict["line"]),
            end_column=v_dict.get("end_column", 1),
            severity=v_dict["severity"],
            rule_id=v_dict["rule_id"],
            message=v_dict["message"],
            code_snippet=v_dict.get("code_snippet", ""),
            fix_suggestion=v_dict.get("fix_suggestion"),
            meta_vars=v_dict.get("meta_vars")
        )
        violations.append(violation)

    # Group violations
    violations_by_file: Dict[str, List[RuleViolation]] = {}
    violations_by_severity: Dict[str, List[RuleViolation]] = {}
    violations_by_rule: Dict[str, List[RuleViolation]] = {}

    for v in violations:
        # By file
        if v.file not in violations_by_file:
            violations_by_file[v.file] = []
        violations_by_file[v.file].append(v)

        # By severity
        if v.severity not in violations_by_severity:
            violations_by_severity[v.severity] = []
        violations_by_severity[v.severity].append(v)

        # By rule
        if v.rule_id not in violations_by_rule:
            violations_by_rule[v.rule_id] = []
        violations_by_rule[v.rule_id].append(v)

    return EnforcementResult(
        summary=data.get("summary", {}),
        violations=violations,
        violations_by_file=violations_by_file,
        violations_by_severity=violations_by_severity,
        violations_by_rule=violations_by_rule,
        rules_executed=data.get("rules_executed", []),
        execution_time_ms=data.get("execution_time_ms", 0),
        files_scanned=data.get("summary", {}).get("files_scanned", 0)
    )


def detect_security_issues_tool(
    project_folder: str,
    language: str,
    issue_types: List[str] | None = None,
    severity_threshold: str = "low",
    max_issues: int = 100
) -> Dict[str, Any]:
    """
    Scan code for security vulnerabilities and common weaknesses.

    This function performs comprehensive security scanning using ast-grep patterns
    and regex-based detection to identify vulnerabilities like SQL injection, XSS,
    command injection, hardcoded secrets, and insecure cryptography.

    **Vulnerability Types:**
    - `sql_injection`: SQL injection via f-strings, .format(), concatenation
    - `xss`: Cross-site scripting via innerHTML, document.write
    - `command_injection`: Command injection via os.system, subprocess, eval/exec
    - `hardcoded_secrets`: API keys, tokens, passwords in source code
    - `insecure_crypto`: Weak hash algorithms (MD5, SHA-1)

    **Severity Levels:**
    - `critical`: Immediate security risk requiring urgent fix
    - `high`: Serious security weakness
    - `medium`: Moderate security concern
    - `low`: Minor security issue or code smell

    **CWE References:**
    Each issue includes CWE (Common Weakness Enumeration) IDs for standardized
    vulnerability classification.

    Args:
        project_folder: Absolute path to project root directory
        language: Programming language (python, javascript, typescript, java)
        issue_types: Types to scan for, or None for all types
        severity_threshold: Minimum severity to report (critical/high/medium/low)
        max_issues: Maximum number of issues to return (0 = unlimited)

    Returns:
        Dictionary containing security scan results with summary and issues

    Example usage:
        # Scan for all security issues
        result = detect_security_issues(
            project_folder="/path/to/project",
            language="python",
            issue_types=["all"],
            severity_threshold="medium"
        )

        # Scan for specific vulnerability types
        result = detect_security_issues(
            project_folder="/path/to/project",
            language="javascript",
            issue_types=["sql_injection", "xss"],
            severity_threshold="high",
            max_issues=50
        )

        print(f"Found {result['summary']['total_issues']} security issues")
        for issue in result['issues']:
            print(f"{issue['severity']}: {issue['title']} at {issue['file']}:{issue['line']}")
    """
    logger = get_logger("tool.detect_security_issues")
    start_time = time.time()

    # Default to all types if not specified
    if issue_types is None:
        issue_types = ["all"]

    logger.info(
        "tool_invoked",
        tool="detect_security_issues",
        project_folder=project_folder,
        language=language,
        issue_types=issue_types,
        severity_threshold=severity_threshold,
        max_issues=max_issues
    )

    try:
        # Run security scan
        result = detect_security_issues_impl(
            project_folder=project_folder,
            language=language,
            issue_types=issue_types,
            severity_threshold=severity_threshold,
            max_issues=max_issues
        )

        execution_time = time.time() - start_time

        logger.info(
            "tool_completed",
            tool="detect_security_issues",
            execution_time_seconds=round(execution_time, 3),
            total_issues=result.summary["total_issues"],
            critical_count=result.summary["critical_count"],
            high_count=result.summary["high_count"],
            files_scanned=result.files_scanned
        )

        # Convert to JSON-serializable format
        return {
            "summary": result.summary,
            "issues": [
                {
                    "file": issue.file,
                    "line": issue.line,
                    "column": issue.column,
                    "end_line": issue.end_line,
                    "end_column": issue.end_column,
                    "issue_type": issue.issue_type,
                    "severity": issue.severity,
                    "title": issue.title,
                    "description": issue.description,
                    "code_snippet": issue.code_snippet,
                    "remediation": issue.remediation,
                    "cwe_id": issue.cwe_id,
                    "confidence": issue.confidence,
                    "references": issue.references
                }
                for issue in result.issues
            ],
            "issues_by_severity": {
                severity: [
                    {
                        "file": issue.file,
                        "line": issue.line,
                        "title": issue.title,
                        "issue_type": issue.issue_type,
                        "cwe_id": issue.cwe_id
                    }
                    for issue in issues
                ]
                for severity, issues in result.issues_by_severity.items()
            },
            "issues_by_type": {
                issue_type: len(issues)
                for issue_type, issues in result.issues_by_type.items()
            },
            "files_scanned": result.files_scanned,
            "execution_time_ms": result.execution_time_ms
        }

    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(
            "tool_failed",
            tool="detect_security_issues",
            execution_time_seconds=round(execution_time, 3),
            error=str(e)[:200]
        )
        sentry_sdk.capture_exception(e, extras={
            "tool": "detect_security_issues",
            "project_folder": project_folder,
            "language": language,
            "issue_types": issue_types,
            "execution_time_seconds": round(execution_time, 3)
        })
        raise


def register_quality_tools(mcp: FastMCP) -> None:
    """Register all quality feature tools with MCP server.

    Args:
        mcp: FastMCP server instance

    Note:
        detect_code_smells is registered in the complexity module's register_complexity_tools() function
        to consolidate code smell detection with complexity analysis.
    """

    @mcp.tool()
    def create_linting_rule(
        rule_name: str = Field(description="Unique rule identifier (e.g., 'no-console-log')"),
        description: str = Field(description="Human-readable description of what the rule checks"),
        pattern: str = Field(description="ast-grep pattern to match (e.g., 'console.log($$$)')"),
        severity: str = Field(description="Severity level: 'error', 'warning', or 'info'"),
        language: str = Field(description="Target language (python, typescript, javascript, java, etc.)"),
        suggested_fix: Optional[str] = Field(default=None, description="Optional replacement pattern or fix suggestion"),
        note: Optional[str] = Field(default=None, description="Additional note or explanation"),
        save_to_project: bool = Field(default=False, description="If True, save rule to project's .ast-grep-rules/"),
        project_folder: Optional[str] = Field(default=None, description="Project folder (required if save_to_project=True)"),
        use_template: Optional[str] = Field(default=None, description="Optional template ID to use as base")
    ) -> Dict[str, Any]:
        """Wrapper that calls the standalone create_linting_rule_tool function."""
        return create_linting_rule_tool(
            rule_name=rule_name,
            description=description,
            pattern=pattern,
            severity=severity,
            language=language,
            suggested_fix=suggested_fix,
            note=note,
            save_to_project=save_to_project,
            project_folder=project_folder,
            use_template=use_template
        )

    @mcp.tool()
    def list_rule_templates(
        language: Optional[str] = Field(default=None, description="Filter by language (python, typescript, javascript, java, etc.)"),
        category: Optional[str] = Field(default=None, description="Filter by category (general, security, performance, style)")
    ) -> Dict[str, Any]:
        """Wrapper that calls the standalone list_rule_templates_tool function."""
        return list_rule_templates_tool(language=language, category=category)

    @mcp.tool()
    def enforce_standards(
        project_folder: str = Field(description="The absolute path to the project folder to scan"),
        language: str = Field(description="The programming language (python, typescript, javascript, java)"),
        rule_set: str = Field(
            default="recommended",
            description="Rule set to use: 'recommended', 'security', 'performance', 'style', 'custom', 'all'"
        ),
        custom_rules: List[str] = Field(
            default_factory=list,
            description="List of custom rule IDs from .ast-grep-rules/ (used with rule_set='custom')"
        ),
        include_patterns: List[str] = Field(
            default_factory=lambda: ["**/*"],
            description="Glob patterns for files to include (e.g., ['src/**/*.py'])"
        ),
        exclude_patterns: List[str] = Field(
            default_factory=lambda: [
                "**/node_modules/**", "**/__pycache__/**", "**/venv/**",
                "**/.venv/**", "**/site-packages/**", "**/dist/**",
                "**/build/**", "**/.git/**", "**/coverage/**"
            ],
            description="Glob patterns for files to exclude"
        ),
        severity_threshold: str = Field(
            default="info",
            description="Only report violations >= this severity ('error', 'warning', 'info')"
        ),
        max_violations: int = Field(
            default=100,
            description="Maximum violations to find (0 = unlimited). Stops execution early when reached."
        ),
        max_threads: int = Field(
            default=4,
            description="Number of parallel threads for rule execution (default: 4)"
        ),
        output_format: str = Field(
            default="json",
            description="Output format: 'json' (structured data) or 'text' (human-readable report)"
        )
    ) -> Dict[str, Any]:
        """Wrapper that calls the standalone enforce_standards_tool function."""
        return enforce_standards_tool(
            project_folder=project_folder,
            language=language,
            rule_set=rule_set,
            custom_rules=custom_rules,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
            severity_threshold=severity_threshold,
            max_violations=max_violations,
            max_threads=max_threads,
            output_format=output_format
        )

    @mcp.tool()
    def apply_standards_fixes(
        violations: List[Dict[str, Any]] = Field(description="List of violations from enforce_standards to fix"),
        language: str = Field(description="Programming language for syntax validation"),
        fix_types: List[str] = Field(
            default_factory=lambda: ["safe"],
            description="Types of fixes to apply: 'safe' (guaranteed-safe), 'suggested' (may need review), 'all'"
        ),
        dry_run: bool = Field(
            default=True,
            description="If True, preview fixes without applying them"
        ),
        create_backup: bool = Field(
            default=True,
            description="If True, create backup before applying fixes"
        )
    ) -> Dict[str, Any]:
        """Wrapper that calls the standalone apply_standards_fixes_tool function."""
        return apply_standards_fixes_tool(
            violations=violations,
            language=language,
            fix_types=fix_types,
            dry_run=dry_run,
            create_backup=create_backup
        )

    @mcp.tool()
    def generate_quality_report(
        enforcement_result: Dict[str, Any] = Field(description="Result dictionary from enforce_standards tool"),
        project_name: str = Field(default="Project", description="Name of the project for report header"),
        output_format: str = Field(default="markdown", description="Report format ('markdown' or 'json')"),
        include_violations: bool = Field(default=True, description="Whether to include detailed violation listings"),
        include_code_snippets: bool = Field(default=False, description="Whether to include code snippets (JSON only)"),
        save_to_file: Optional[str] = Field(default=None, description="Optional file path to save the report")
    ) -> Dict[str, Any]:
        """Wrapper that calls the standalone generate_quality_report_tool function."""
        return generate_quality_report_tool(
            enforcement_result=enforcement_result,
            project_name=project_name,
            output_format=output_format,
            include_violations=include_violations,
            include_code_snippets=include_code_snippets,
            save_to_file=save_to_file
        )

    @mcp.tool()
    def detect_security_issues(
        project_folder: str = Field(description="Absolute path to project root directory"),
        language: str = Field(description="Programming language (python, javascript, typescript, java)"),
        issue_types: List[str] | None = Field(
            default=None,
            description="Types to scan for: 'sql_injection', 'xss', 'command_injection', 'hardcoded_secrets', 'insecure_crypto', or None for all"
        ),
        severity_threshold: str = Field(
            default="low",
            description="Minimum severity to report: 'critical', 'high', 'medium', 'low'"
        ),
        max_issues: int = Field(
            default=100,
            description="Maximum number of issues to return (0 = unlimited)"
        )
    ) -> Dict[str, Any]:
        """Wrapper that calls the standalone detect_security_issues_tool function."""
        return detect_security_issues_tool(
            project_folder=project_folder,
            language=language,
            issue_types=issue_types,
            severity_threshold=severity_threshold,
            max_issues=max_issues
        )
