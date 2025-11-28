#!/usr/bin/env python3
"""Migrate test imports from main.py to modular structure.

This script updates all test files to import from the proper modular structure
instead of from main.py, enabling the removal of backward compatibility imports.
"""
from ast_grep_mcp.utils.console_logger import console

import os
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Module mapping: function/class name -> modular import path
MODULE_MAPPING: Dict[str, str] = {
    # Core
    'get_supported_languages': 'ast_grep_mcp.core.config',
    'validate_config_file': 'ast_grep_mcp.core.config',
    'QueryCache': 'ast_grep_mcp.core.cache',

    # Features - Deduplication
    'calculate_similarity': 'ast_grep_mcp.features.deduplication.detector',
    'normalize_code': 'ast_grep_mcp.features.deduplication.detector',
    'group_duplicates': 'ast_grep_mcp.features.deduplication.detector',
    'calculate_deduplication_score': 'ast_grep_mcp.features.deduplication.ranker',
    'rank_deduplication_candidates': 'ast_grep_mcp.features.deduplication.ranker',
    'analyze_duplicate_variations': 'ast_grep_mcp.features.deduplication.analyzer',
    'build_diff_tree': 'ast_grep_mcp.features.deduplication.analyzer',
    'build_nested_diff_tree': 'ast_grep_mcp.features.deduplication.analyzer',
    'format_alignment_diff': 'ast_grep_mcp.features.deduplication.analyzer',
    'ParameterType': 'ast_grep_mcp.features.deduplication.analyzer',
    '_infer_single_value_type': 'ast_grep_mcp.features.deduplication.analyzer',
    '_infer_from_identifier_name': 'ast_grep_mcp.features.deduplication.analyzer',
    '_detect_nested_function_call': 'ast_grep_mcp.features.deduplication.analyzer',
    'generate_parameter_name': 'ast_grep_mcp.features.deduplication.analyzer',
    'identify_varying_identifiers': 'ast_grep_mcp.features.deduplication.analyzer',
    'infer_parameter_type': 'ast_grep_mcp.features.deduplication.analyzer',
    'VariationSeverity': 'ast_grep_mcp.features.deduplication.analyzer',
    'classify_variations': 'ast_grep_mcp.features.deduplication.analyzer',
    'detect_conditional_variations': 'ast_grep_mcp.features.deduplication.analyzer',
    'generate_deduplication_recommendation': 'ast_grep_mcp.features.deduplication.recommendations',
    '_generate_dedup_recommendation': 'ast_grep_mcp.features.deduplication.recommendations',
    '_generate_refactoring_strategies': 'ast_grep_mcp.features.deduplication.recommendations',
    'generate_refactoring_suggestions': 'ast_grep_mcp.features.deduplication.recommendations',
    'get_test_coverage_for_files': 'ast_grep_mcp.features.deduplication.coverage',
    '_check_test_file_references_source': 'ast_grep_mcp.features.deduplication.coverage',
    '_get_potential_test_paths': 'ast_grep_mcp.features.deduplication.coverage',
    '_assess_breaking_change_risk': 'ast_grep_mcp.features.deduplication.impact',
    '_estimate_lines_changed': 'ast_grep_mcp.features.deduplication.impact',
    '_extract_function_names_from_code': 'ast_grep_mcp.features.deduplication.impact',
    '_find_external_call_sites': 'ast_grep_mcp.features.deduplication.impact',
    '_find_import_references': 'ast_grep_mcp.features.deduplication.impact',
    'create_enhanced_duplication_response': 'ast_grep_mcp.features.deduplication.reporting',
    'diff_preview_to_dict': 'ast_grep_mcp.features.deduplication.applicator',
    'generate_diff_from_file_paths': 'ast_grep_mcp.features.deduplication.applicator',
    'generate_file_diff': 'ast_grep_mcp.features.deduplication.applicator',
    'generate_multi_file_diff': 'ast_grep_mcp.features.deduplication.applicator',
    'generate_function_signature': 'ast_grep_mcp.features.deduplication.generator',
    'generate_function_body': 'ast_grep_mcp.features.deduplication.generator',
    'generate_python_function': 'ast_grep_mcp.features.deduplication.generator',
    'generate_typescript_function': 'ast_grep_mcp.features.deduplication.generator',
    'generate_javascript_function': 'ast_grep_mcp.features.deduplication.generator',
    'generate_java_method': 'ast_grep_mcp.features.deduplication.generator',
    'generate_docstring': 'ast_grep_mcp.features.deduplication.generator',
    'generate_type_annotations': 'ast_grep_mcp.features.deduplication.generator',
    'format_python_params': 'ast_grep_mcp.features.deduplication.generator',
    'format_typescript_params': 'ast_grep_mcp.features.deduplication.generator',
    'format_java_params': 'ast_grep_mcp.features.deduplication.generator',
    'format_arguments_for_call': 'ast_grep_mcp.features.deduplication.generator',
    'preserve_call_site_indentation': 'ast_grep_mcp.features.deduplication.generator',
    '_detect_python_import_point': 'ast_grep_mcp.features.deduplication.generator',
    '_detect_js_import_point': 'ast_grep_mcp.features.deduplication.generator',
    '_detect_java_import_point': 'ast_grep_mcp.features.deduplication.generator',
    '_detect_generic_import_point': 'ast_grep_mcp.features.deduplication.generator',
    '_extract_identifiers': 'ast_grep_mcp.features.deduplication.generator',
    '_extract_imports_with_names': 'ast_grep_mcp.features.deduplication.generator',
    '_remove_import_lines': 'ast_grep_mcp.features.deduplication.generator',
    'generate_import_statement': 'ast_grep_mcp.features.deduplication.generator',
    'identify_unused_imports': 'ast_grep_mcp.features.deduplication.generator',
    'resolve_import_path': 'ast_grep_mcp.features.deduplication.generator',
    'analyze_import_overlap': 'ast_grep_mcp.features.deduplication.generator',
    'detect_import_variations': 'ast_grep_mcp.features.deduplication.generator',
    'detect_internal_dependencies': 'ast_grep_mcp.features.deduplication.generator',
    'extract_imports_from_files': 'ast_grep_mcp.features.deduplication.generator',

    # Features - Rewrite
    'create_backup': 'ast_grep_mcp.features.rewrite.backup',
    'restore_from_backup': 'ast_grep_mcp.features.rewrite.backup',
    '_validate_code_for_language': 'ast_grep_mcp.features.rewrite.service',
    '_suggest_syntax_fix': 'ast_grep_mcp.features.rewrite.service',
    'validate_syntax': 'ast_grep_mcp.features.rewrite.service',

    # Models - Complexity
    'ComplexityStorage': 'ast_grep_mcp.models.complexity',
    'ComplexityThresholds': 'ast_grep_mcp.models.complexity',
    'FunctionComplexity': 'ast_grep_mcp.models.complexity',

    # Models - Standards
    'LintingRule': 'ast_grep_mcp.models.standards',
    'RuleTemplate': 'ast_grep_mcp.models.standards',
    'RuleValidationResult': 'ast_grep_mcp.models.standards',
    'RuleValidationError': 'ast_grep_mcp.models.standards',
    'RuleStorageError': 'ast_grep_mcp.models.standards',
    'RuleViolation': 'ast_grep_mcp.models.standards',
    'RuleExecutionContext': 'ast_grep_mcp.models.standards',
    'EnforcementResult': 'ast_grep_mcp.models.standards',
    'RuleSet': 'ast_grep_mcp.models.standards',

    # Features - Complexity
    'calculate_nesting_depth': 'ast_grep_mcp.features.complexity.analyzer',
    'get_complexity_patterns': 'ast_grep_mcp.features.complexity.analyzer',
    'get_complexity_level': 'ast_grep_mcp.features.complexity.metrics',

    # Features - Quality
    '_validate_rule_pattern': 'ast_grep_mcp.features.quality.validator',
    '_validate_rule_definition': 'ast_grep_mcp.features.quality.validator',
    '_save_rule_to_project': 'ast_grep_mcp.features.quality.rules',
    '_load_rule_from_file': 'ast_grep_mcp.features.quality.rules',
    '_get_available_templates': 'ast_grep_mcp.features.quality.rules',
    '_execute_rule': 'ast_grep_mcp.features.quality.enforcer',
    '_execute_rules_batch': 'ast_grep_mcp.features.quality.enforcer',
    '_filter_violations_by_severity': 'ast_grep_mcp.features.quality.enforcer',
    '_format_violation_report': 'ast_grep_mcp.features.quality.enforcer',
    '_group_violations_by_file': 'ast_grep_mcp.features.quality.enforcer',
    '_group_violations_by_rule': 'ast_grep_mcp.features.quality.enforcer',
    '_group_violations_by_severity': 'ast_grep_mcp.features.quality.enforcer',
    '_load_custom_rules': 'ast_grep_mcp.features.quality.enforcer',
    '_load_rule_set': 'ast_grep_mcp.features.quality.enforcer',
    '_parse_match_to_violation': 'ast_grep_mcp.features.quality.enforcer',
    '_should_exclude_file': 'ast_grep_mcp.features.quality.enforcer',
    '_template_to_linting_rule': 'ast_grep_mcp.features.quality.enforcer',
    'RULE_SETS': 'ast_grep_mcp.features.quality.enforcer',

    # Utils
    '_basic_python_format': 'ast_grep_mcp.utils.formatters',
    '_format_python_line': 'ast_grep_mcp.utils.formatters',
    'format_generated_code': 'ast_grep_mcp.utils.formatters',
    'format_java_code': 'ast_grep_mcp.utils.formatters',
    'format_javascript_code': 'ast_grep_mcp.utils.formatters',
    'format_python_code': 'ast_grep_mcp.utils.formatters',
    'format_typescript_code': 'ast_grep_mcp.utils.formatters',
    'filter_files_by_size': 'ast_grep_mcp.utils.text',
}


def extract_main_imports(file_content: str) -> Tuple[List[str], Set[int]]:
    """Extract all imports from main and their line numbers."""
    imports: List[str] = []
    line_numbers: Set[int] = set()

    lines = file_content.split('\n')

    # Find multi-line imports
    in_main_import = False
    import_start_line = -1

    for i, line in enumerate(lines):
        if line.strip().startswith('from main import'):
            if '(' in line:
                in_main_import = True
                import_start_line = i
                line_numbers.add(i)
            else:
                # Single-line import
                match = re.match(r'from main import\s+(.+)', line)
                if match:
                    items = [item.strip() for item in match.group(1).split(',')]
                    imports.extend(items)
                    line_numbers.add(i)
        elif in_main_import:
            line_numbers.add(i)
            if ')' in line:
                in_main_import = False
            # Extract imports from this line
            stripped = line.strip().rstrip(',').rstrip(')')
            if stripped and not stripped.startswith('#'):
                imports.append(stripped)

    return imports, line_numbers


def group_imports_by_module(imports: List[str]) -> Dict[str, List[str]]:
    """Group imported names by their target module."""
    groups: Dict[str, List[str]] = {}

    for name in imports:
        if name in MODULE_MAPPING:
            module = MODULE_MAPPING[name]
            if module not in groups:
                groups[module] = []
            groups[module].append(name)
        else:
            console.warning(f"WARNING: No module mapping for '{name}'")

    return groups


def generate_new_imports(groups: Dict[str, List[str]]) -> List[str]:
    """Generate new import statements grouped by module."""
    import_lines: List[str] = []

    for module in sorted(groups.keys()):
        names = sorted(groups[module])
        if len(names) == 1:
            import_lines.append(f"from {module} import {names[0]}")
        else:
            import_lines.append(f"from {module} import (")
            for i, name in enumerate(names):
                comma = "," if i < len(names) - 1 else ""
                import_lines.append(f"    {name}{comma}")
            import_lines.append(")")

    return import_lines


def migrate_file(filepath: Path, dry_run: bool = True) -> bool:
    """Migrate a single test file from main imports to modular imports."""
    with open(filepath, 'r') as f:
        content = f.read()

    # Check if file has main imports
    if 'from main import' not in content:
        return False

    console.log(f"\n{'[DRY RUN] ' if dry_run else ''}Processing: {filepath}")

    # Extract imports from main
    imports, line_numbers = extract_main_imports(content)

    if not imports:
        return False

    console.log(f"  Found {len(imports)} imports from main")

    # Group by target module
    groups = group_imports_by_module(imports)

    # Generate new import statements
    new_import_lines = generate_new_imports(groups)

    # Remove old import lines
    lines = content.split('\n')
    new_lines = [line for i, line in enumerate(lines) if i not in line_numbers]

    # Find insertion point (after existing imports)
    insert_idx = 0
    for i, line in enumerate(new_lines):
        if line.strip().startswith('import ') or line.strip().startswith('from '):
            insert_idx = i + 1
        elif line.strip() and not line.strip().startswith('#'):
            # Stop at first non-import, non-comment line
            break

    # Insert new imports
    for import_line in reversed(new_import_lines):
        new_lines.insert(insert_idx, import_line)

    new_content = '\n'.join(new_lines)

    # Show diff
    console.log(f"  Will add {len(new_import_lines)} new import lines")
    for line in new_import_lines:
        console.log(f"    + {line}")

    if not dry_run:
        with open(filepath, 'w') as f:
            f.write(new_content)
        console.success(f"  ✓ Updated {filepath}")

    return True


def main():
    """Main migration script."""
    import argparse

    parser = argparse.ArgumentParser(description='Migrate test imports from main to modular structure')
    parser.add_argument('--apply', action='store_true', help='Apply changes (default is dry-run)')
    parser.add_argument('--file', type=str, help='Migrate a specific file')
    args = parser.parse_args()

    dry_run = not args.apply

    if dry_run:
        console.log("=" * 80)
        console.log("DRY RUN MODE - No files will be modified")
        console.log("Run with --apply to apply changes")
        console.log("=" * 80)

    if args.file:
        # Migrate single file
        filepath = Path(args.file)
        if not filepath.exists():
            console.error(f"ERROR: File not found: {filepath}")
            return 1

        migrated = migrate_file(filepath, dry_run=dry_run)
        if not migrated:
            console.log(f"No migration needed for {filepath}")
    else:
        # Migrate all test files
        test_dir = Path('tests')
        test_files = list(test_dir.rglob('*.py'))

        console.log(f"Found {len(test_files)} test files")

        migrated_count = 0
        for filepath in sorted(test_files):
            if migrate_file(filepath, dry_run=dry_run):
                migrated_count += 1

        console.log("\n" + "=" * 80)
        console.success(f"Migration complete: {migrated_count} files {'would be' if dry_run else 'were'} updated")

        if dry_run:
            console.log("\nRun with --apply to apply changes")

    return 0


if __name__ == '__main__':
    exit(main())
