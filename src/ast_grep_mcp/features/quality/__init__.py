"""Code quality and standards feature.

This feature provides:
- Code smell detection (long functions, parameter bloat, deep nesting, large classes, magic numbers)
- Linting rule management (create, validate, save, load)
- Standards enforcement (execute rules in parallel, report violations)

Modules:
- smells: Code smell detection implementation
- rules: Rule templates and CRUD operations
- validator: Rule validation logic
- enforcer: Standards enforcement engine
- tools: MCP tool registrations
"""

from ast_grep_mcp.features.quality.smells import (
    detect_code_smells_impl,
    _count_function_parameters,
    _find_magic_numbers,
    _extract_classes_from_file,
)
from ast_grep_mcp.features.quality.rules import (
    RULE_TEMPLATES,
    get_available_templates,
    create_rule_from_template,
    save_rule_to_project,
    load_rule_from_file,
    load_rules_from_project,
    delete_rule_from_project
)
from ast_grep_mcp.features.quality.validator import (
    validate_rule_pattern,
    validate_rule_definition,
    validate_linting_rules_impl
)
from ast_grep_mcp.features.quality.enforcer import (
    RULE_SETS,
    template_to_linting_rule,
    load_custom_rules,
    load_rule_set,
    parse_match_to_violation,
    should_exclude_file,
    execute_rule,
    execute_rules_batch,
    group_violations_by_file,
    group_violations_by_severity,
    group_violations_by_rule,
    filter_violations_by_severity,
    format_violation_report,
    enforce_standards_impl
)
from ast_grep_mcp.features.quality.tools import register_quality_tools

__all__ = [
    # Smells
    "detect_code_smells_impl",
    "_count_function_parameters",
    "_find_magic_numbers",
    "_extract_classes_from_file",
    # Rules
    "RULE_TEMPLATES",
    "get_available_templates",
    "create_rule_from_template",
    "save_rule_to_project",
    "load_rule_from_file",
    "load_rules_from_project",
    "delete_rule_from_project",
    # Validator
    "validate_rule_pattern",
    "validate_rule_definition",
    "validate_linting_rules_impl",
    # Enforcer
    "RULE_SETS",
    "template_to_linting_rule",
    "load_custom_rules",
    "load_rule_set",
    "parse_match_to_violation",
    "should_exclude_file",
    "execute_rule",
    "execute_rules_batch",
    "group_violations_by_file",
    "group_violations_by_severity",
    "group_violations_by_rule",
    "filter_violations_by_severity",
    "format_violation_report",
    "enforce_standards_impl",
    # Tools
    "register_quality_tools",
]
